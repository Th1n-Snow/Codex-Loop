from dataclasses import replace
from datetime import datetime,timedelta
from pathlib import Path
import tempfile,unittest
from sentinel.schedule import MULTI,multi_schedule_summary,normalize_multi_times,schedule_summary
from sentinel.app_state import AppSettings,AppStateStore,ProviderViewState,automation_decision
from sentinel.app_controller import ApplicationController
from sentinel.presentation import operational_presentation

def at(hour,minute=0,second=0,day=18):
    return datetime(2026,10,day,hour,minute,second).timestamp()

TIMES=((12,0),(17,0),(21,0))
class MultiTimeScheduleTests(unittest.TestCase):
    def test_sorted_unique_and_invalid(self):
        self.assertEqual(TIMES,normalize_multi_times([(21,0),(12,0),(17,0),(12,0)]))
        for value in [[(24,0)],[(12,60)],[(True,0)],[(1.2,0)],[(12,)],None]:
            with self.subTest(value=value),self.assertRaises(ValueError):normalize_multi_times(value)

    def test_each_slot_is_due_only_once_and_future_slot_is_next(self):
        last=None
        for hour,next_hour in [(12,17),(17,21),(21,12)]:
            now=at(hour,second=30)
            summary=multi_schedule_summary(now,TIMES,last)
            self.assertTrue(summary.due)
            self.assertEqual(at(hour),summary.next_action_at)
            last=summary.next_action_at
            following=multi_schedule_summary(now,TIMES,last)
            self.assertFalse(following.due)
            self.assertEqual(next_hour,datetime.fromtimestamp(following.next_action_at).hour)

    def test_no_early_or_late_backfill(self):
        for now in [at(11,59,59),at(12,3),at(16,30),at(22)]:
            self.assertFalse(multi_schedule_summary(now,TIMES).due)
        self.assertEqual(at(17),multi_schedule_summary(at(15),TIMES).next_action_at)

    def test_midnight_and_previous_day_grace(self):
        values=((0,0),(23,59))
        self.assertEqual(at(0,day=19),multi_schedule_summary(at(23,59,30),values,at(23,59)).next_action_at)
        summary=multi_schedule_summary(at(0,0,30,day=19),((23,59),))
        self.assertTrue(summary.due)
        self.assertEqual(at(23,59),summary.next_action_at)

    def test_empty_and_first_window_do_not_start_outside_appointments(self):
        self.assertIsNone(multi_schedule_summary(at(12),()).next_action_at)
        self.assertEqual(at(17),schedule_summary(MULTI,boundary_reset_at=None,now=at(14),multi_times=TIMES).next_action_at)
        state=ProviderViewState.waiting('codex','Codex',installed=True,runtime_identity='r')
        kw=dict(compatible_runtime_identity='r',checked_runtime_identity='r',schedule_mode=MULTI,multi_times=TIMES)
        self.assertEqual('WAIT',automation_decision(True,state,now=at(14),**kw).action)
        self.assertEqual('TIMED',automation_decision(True,state,now=at(17),**kw).action)

    def test_rollover_buffer_and_off_pause(self):
        state=replace(ProviderViewState.waiting('codex','Codex',installed=True,runtime_identity='r'),reset_at=int(at(17)),last_verified_at=at(16),quota_state='ANCHORED')
        kw=dict(compatible_runtime_identity='r',checked_runtime_identity='r',schedule_mode=MULTI,multi_times=TIMES)
        self.assertEqual('WAIT',automation_decision(True,state,now=at(17,0,30),**kw).action)
        self.assertEqual('TIMED',automation_decision(True,state,now=at(17,1),**kw).action)
        self.assertEqual('NONE',automation_decision(False,state,now=at(17,1),**kw).action)
        self.assertEqual('WAIT',automation_decision(True,state,now=at(17,1),paused_until=at(18),**kw).action)

    def test_persisted_claim_survives_restart_and_does_not_change_quota(self):
        with tempfile.TemporaryDirectory() as folder:
            store=AppStateStore(Path(folder)/'state.json')
            controller=ApplicationController([],store)
            controller.settings=AppSettings(automation_enabled=True)
            self.assertTrue(controller.set_multi_start_times([(21,0),(12,0),(17,0)]))
            self.assertTrue(controller.claim_multi_slot(now=at(12,0,30),status='已提交预热检查'))
            self.assertFalse(controller.claim_multi_slot(now=at(12,1),status='duplicate'))
            saved=store.load()
            self.assertEqual(TIMES,saved.multi_start_times)
            self.assertEqual(MULTI,saved.schedule_mode)
            self.assertFalse(multi_schedule_summary(at(12,1),saved.multi_start_times,saved.multi_last_slot).due)
            self.assertEqual((12,0),tuple(map(int,datetime.fromtimestamp(saved.tomorrow_first_start(at(12))).strftime('%H %M').split())))

    def test_dashboard_next_action_uses_saved_appointments_even_with_active_window(self):
        state=replace(ProviderViewState.waiting('codex','Codex',installed=True,runtime_identity='r'),status='Ready',reset_at=int(at(23)),last_verified_at=at(18),usage_checked_at=at(18),quota_state='ANCHORED',weekly_used_percent=10)
        settings=AppSettings(automation_enabled=True,schedule_mode=MULTI,multi_start_times=TIMES,compatible_runtime_identities={'codex':'r'},checked_runtime_identities={'codex':'r'})
        view=operational_presentation(settings,state,now=at(19))
        self.assertEqual('active_window',view.kind)
        self.assertIn('21:00',view.next_action.replace('9:00 PM','21:00'))
