import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,time,unittest
from pathlib import Path
from dataclasses import replace
from datetime import datetime
from PySide6.QtCore import QTime,QPoint,QPointF,Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication,QDateTimeEdit
from sentinel.app_state import AppSettings,AppStateStore,ProviderViewState
from sentinel.app_controller import ApplicationController
from sentinel.appointments import BackgroundAppointments
from sentinel.schedule import MULTI
from sentinel.ui_components import TimeEntry
from sentinel.history import SafeHistory
from sentinel.provider_runtime import CodexOperationRunner
from test_provider_runtime import FakeClient,FakeSession,payload

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=datetime(2026,10,19,12,0).timestamp()
        self.c=ApplicationController([],AppStateStore(Path(self.tmp.name)/'state.json'))
        self.c.settings=AppSettings(automation_enabled=True,schedule_mode=MULTI,multi_start_times=((12,0),(12,1)),compatible_runtime_identities={'codex':'r'})
        self.c.states={'codex':ProviderViewState('codex','Codex',True,True,'Ready','fixed','r',reset_at=int(self.now+300),last_verified_at=self.now-100,quota_state='ANCHORED')}
        self.actions=[];self.prepares=[];self.busy={}
        self.q=self.make_queue()
    def make_queue(self):return BackgroundAppointments(self.c,lambda *args:self.actions.append(args),lambda *args:self.prepares.append(args),lambda:self.busy)
    def test_active_window_is_queued_and_coalesced_until_reset_buffer(self):
        self.q.tick(self.now)
        self.assertEqual(self.now,self.c.settings.multi_pending_slot)
        self.q.tick(self.now+61)
        self.assertEqual(self.now,self.c.settings.multi_pending_slot)
        self.assertFalse(self.actions)
        self.q.tick(self.now+359);self.assertFalse(self.actions)
        self.q.tick(self.now+360)
        self.assertEqual([('codex','rollover',self.now)],self.actions)
        self.q.tick(self.now+361);self.assertEqual(1,len(self.actions))
    def test_restart_uses_durable_pending_without_duplicate(self):
        self.q.tick(self.now)
        self.c.settings=self.c.store.load();self.q=self.make_queue()
        self.q.tick(self.now+360)
        self.assertEqual(1,len(self.actions))
        self.c.settings=self.c.store.load();self.make_queue().tick(self.now+361)
        self.assertEqual(1,len(self.actions))
    def test_sleep_past_grace_does_not_backfill(self):
        self.q.tick(self.now);self.q.tick(self.now+900)
        self.assertFalse(self.actions);self.assertIsNone(self.c.settings.multi_pending_slot)
    def test_pausing_cancels_pending(self):
        self.q.tick(self.now)
        self.c.settings=replace(self.c.settings,automation_paused_until=self.now+900)
        self.q.tick(self.now+100)
        self.assertIsNone(self.c.settings.multi_pending_slot);self.assertFalse(self.actions)
    def test_runtime_change_cancels_old_pending(self):
        self.q.tick(self.now)
        self.c.states['codex']=replace(self.c.states['codex'],runtime_identity='new')
        self.q.tick(self.now+360)
        self.assertFalse(self.actions);self.assertIsNone(self.c.settings.multi_pending_slot)
    def test_prepare_before_slot_is_read_only_and_once(self):
        self.q.tick(self.now-80);self.q.tick(self.now-40)
        self.assertEqual([('codex','r')],self.prepares);self.assertFalse(self.actions)
    def test_new_window_started_elsewhere_satisfies_pending(self):
        self.q.tick(self.now)
        self.c.states['codex']=replace(self.c.states['codex'],reset_at=int(self.now+18000),last_verified_at=self.now+350)
        self.q.tick(self.now+360)
        self.assertFalse(self.actions);self.assertIsNone(self.c.settings.multi_pending_slot)
    def test_disabled_and_storage_failure_never_launch(self):
        self.c.settings=replace(self.c.settings,automation_enabled=False)
        self.q.tick(self.now);self.assertFalse(self.prepares);self.assertFalse(self.actions)
        self.c.settings=replace(self.c.settings,automation_enabled=True)
        self.c._save_settings=lambda candidate:False
        self.q.tick(self.now+360);self.assertFalse(self.actions)

class PreparedConnectionTests(unittest.TestCase):
    def test_preparation_reuses_connection_but_still_rechecks_quota(self):
        with tempfile.TemporaryDirectory() as folder:
            client=FakeClient([payload(18000)]);session=FakeSession(client);created=[]
            def factory():created.append(1);return session
            now=[100.]
            runner=CodexOperationRunner(SafeHistory(Path(folder)/'history.jsonl'),session_factory=factory,clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))
            self.assertTrue(runner.prepare_connection('r'))
            self.assertEqual(0,client.turn_calls);self.assertEqual(0,client.thread_calls)
            runner.run('bootstrap',runtime_identity='r',scheduled_at=100)
            self.assertEqual(1,len(created));self.assertEqual(5,client.read_calls)
            self.assertTrue(session.closed);self.assertEqual(0,client.turn_calls)
    def test_real_trigger_path_records_submission_and_confirmation_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            now=[100.]
            class Client(FakeClient):
                anchor=None
                def read_rate_limits(self):
                    return payload(self.anchor or int(now[0]+18000))
                def start_turn(self, params):
                    super().start_turn(params)
                    self.anchor=int(now[0]+18000)
            client=Client([])
            history=SafeHistory(Path(folder)/'history.jsonl')
            runner=CodexOperationRunner(history,session_factory=lambda:FakeSession(client),clock=lambda:now[0],sleep=lambda seconds:now.__setitem__(0,now[0]+seconds))
            result=runner.run('bootstrap',runtime_identity='r',scheduled_at=90)
            self.assertEqual('ANCHOR_VERIFIED',result.outcome)
            stages=history.timing_records()[history.trigger_attempts()[0].attempt_id]
            self.assertEqual(90,stages['planned_at'])
            self.assertEqual(100,stages['preflight_started_at'])
            self.assertEqual(130,stages['request_submitted_at'])
            self.assertEqual(130,stages['request_completed_at'])
            self.assertEqual(170,stages['window_confirmed_at'])
            self.assertEqual(1,client.turn_calls)

    def test_timing_roundtrip_keeps_exact_stage_times_and_old_history_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            h=SafeHistory(Path(folder)/'h.jsonl')
            a=h.reserve_trigger(mode='bootstrap',idempotency_key='bootstrap:test',boundary_reset_at=None,model='test',reasoning_effort='low',now=100)
            h.record_timing(a.attempt_id,planned_at=90,preflight_started_at=100,request_submitted_at=135)
            h.record_timing(a.attempt_id,request_completed_at=150,window_confirmed_at=190)
            self.assertEqual(135,h.timing_records()[a.attempt_id]['request_submitted_at'])
            self.assertEqual(190,h.timing_records()[a.attempt_id]['window_confirmed_at'])
            self.assertEqual('reserved',h.trigger_attempts()[0].state)

class WheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def event(self):return QWheelEvent(QPointF(30,10),QPointF(30,10),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    def test_only_selected_section_changes_time(self):
        editor=TimeEntry(QTime(12,30));editor.setDisplayFormat('HH:mm');editor.show();editor.setFocus();self.app.processEvents()
        editor.lineEdit().deselect()
        e=self.event();editor.wheelEvent(e)
        self.assertEqual(QTime(12,30),editor.time());self.assertFalse(e.isAccepted())
        editor.setCurrentSection(QDateTimeEdit.Section.HourSection);editor.lineEdit().setSelection(0,2)
        editor.wheelEvent(self.event())
        self.assertEqual(QTime(13,30),editor.time())
        editor.clearFocus();editor.wheelEvent(self.event())
        self.assertEqual(QTime(13,30),editor.time());editor.close()
