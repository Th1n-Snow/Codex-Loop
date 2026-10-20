import os,tempfile,time,unittest,json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from dataclasses import replace
from datetime import datetime
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from sentinel.app_state import AppSettings,AppStateStore,automation_decision,AutomationDecision
from sentinel.app_controller import ApplicationController
from sentinel.appointments import BackgroundAppointments
from sentinel.desktop import MainWindow
from sentinel.schedule import MULTI,CONTINUOUS,schedule_summary
from test_local_self_test import Provider,Startup,state

class ScheduledOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_default_is_multi_and_continuous_summary_can_never_be_due(self):
        self.assertEqual(MULTI,AppSettings().schedule_mode)
        for now in (1000,1060,50000):
            s=schedule_summary(CONTINUOUS,boundary_reset_at=1000,now=now)
            self.assertFalse(s.due);self.assertIsNone(s.next_action_at)
    def test_legacy_enabled_config_migrates_disabled_and_clears_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'state.json'
            p.write_text(json.dumps({'settings':{'automation_enabled':True,'schedule_mode':'continuous','multi_start_times':[[8,0],[18,0]],'multi_pending_slot':1000,'multi_pending_due':1060,'multi_pending_runtime':'r'}}))
            settings=AppStateStore(p).load()
            self.assertEqual(MULTI,settings.schedule_mode);self.assertFalse(settings.automation_enabled)
            self.assertEqual(((8,0),(18,0)),settings.multi_start_times)
            self.assertIsNone(settings.multi_pending_slot);self.assertIsNone(settings.multi_pending_due)
    def test_existing_multi_config_and_waiting_slot_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            store=AppStateStore(Path(folder)/'state.json')
            s=AppSettings(automation_enabled=True,multi_start_times=((8,0),(18,0)),multi_pending_slot=1000,multi_pending_due=1060,multi_pending_runtime='r')
            store.save(s,{})
            self.assertEqual(s,store.load())
    def test_expired_boundary_never_creates_a_request_without_an_appointment(self):
        now=datetime(2026,10,20,14,30).timestamp()
        for reset in (now-60,now-600,now-18000):
            s=state(reset_at=int(reset),last_verified_at=reset-20)
            for mode in (CONTINUOUS,MULTI):
                d=automation_decision(True,s,now=now,compatible_runtime_identity='r',schedule_mode=mode,multi_times=((8,0),(18,0)))
                self.assertEqual('WAIT',d.action)
            with tempfile.TemporaryDirectory() as folder:
                c=ApplicationController([],AppStateStore(Path(folder)/'state.json'))
                c.settings=AppSettings(automation_enabled=True,multi_start_times=((8,0),(18,0)),compatible_runtime_identities={'codex':'r'})
                c.states={'codex':s};sent=[]
                q=BackgroundAppointments(c,lambda *args:sent.append(args),lambda *_:None,lambda:{})
                q.tick(now);q.tick(now+60)
                self.assertEqual([],sent);self.assertIsNone(c.settings.multi_pending_slot)
    def test_schedule_mode_api_cannot_enable_continuous(self):
        with tempfile.TemporaryDirectory() as folder:
            c=ApplicationController([],AppStateStore(Path(folder)/'state.json'))
            with self.assertRaises(ValueError):c.set_schedule_mode(CONTINUOUS)
    def test_desktop_ignores_any_stray_rollover_decision(self):
        with tempfile.TemporaryDirectory() as folder:
            s=state();provider=Provider(s);c=ApplicationController([provider],AppStateStore(Path(folder)/'state.json'))
            c.settings=AppSettings(automation_enabled=True);c.states={'codex':s}
            w=MainWindow(c,{'codex':provider},Startup())
            w.automation_timer.stop();w.usage_sync_timer.stop();w.clock_timer.stop()
            with patch.object(w.appointments,'tick'),patch.object(c,'refresh_local_states'),patch.object(c,'decisions',return_value={'codex':AutomationDecision('ROLLOVER','legacy')}),patch.object(w,'_start_operation') as start:
                w.evaluate_automation(now=time.time())
                start.assert_not_called()
            w.close();w.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
