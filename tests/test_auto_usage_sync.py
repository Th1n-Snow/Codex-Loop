import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication
from sentinel.auto_sync import UsageAutoSync
from sentinel.multi_time_ui import MultiTimePanel
from sentinel.app_state import AppSettings,AppStateStore
from sentinel.app_controller import ApplicationController
from sentinel.desktop import MainWindow
from sentinel.provider_runtime import ProviderOperationResult
from test_local_self_test import Provider,Startup,state

class AutoSyncPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now=10000
        self.state=state(usage_checked_at=9800,reset_at=20000)
        self.settings=AppSettings(compatible_runtime_identities={'codex':'r'})
        self.calls=[]
        self.c=SimpleNamespace(states={'codex':self.state},settings=self.settings,persistence_error=None)
        self.w=SimpleNamespace(controller=self.c,active_operations={},isVisible=lambda:True,
            isMinimized=lambda:False,pages=SimpleNamespace(currentIndex=lambda:0),
            start_usage_sync=self.start)
        self.policy=UsageAutoSync(self.w)
    def start(self,pid,**kwargs):
        self.calls.append((pid,kwargs));self.w.active_operations[pid]='sync'
    def test_dashboard_refreshes_stale_data_and_does_not_overlap(self):
        self.policy.tick(self.now);self.policy.tick(self.now+5)
        self.assertEqual([('codex',{'automatic':True})],self.calls)
    def test_background_waits_five_minutes_and_foreground_refreshes_when_returning(self):
        self.w.isVisible=lambda:False
        self.policy.tick(self.now);self.assertFalse(self.calls)
        self.w.isVisible=lambda:True
        self.policy.tick(self.now);self.assertEqual(1,len(self.calls))
    def test_recent_sync_from_any_operation_suppresses_poll(self):
        self.c.states['codex']=replace(self.state,usage_checked_at=9990)
        self.policy.tick(self.now);self.assertFalse(self.calls)
    def test_failure_backoff_does_not_burst_on_resume(self):
        self.policy.finished(self.now,success=False)
        self.policy.tick(self.now+299);self.assertFalse(self.calls)
        self.policy.tick(self.now+300);self.assertEqual(1,len(self.calls))
    def test_schedule_preparation_and_waiting_queue_take_priority(self):
        for settings in (replace(self.settings,automation_enabled=True,multi_pending_due=10060),):
            self.c.settings=settings
            self.policy.tick(self.now);self.assertFalse(self.calls)
        self.c.settings=self.settings
        self.w.active_operations['codex']='verify'
        self.policy.tick(self.now);self.assertFalse(self.calls)
    def test_unknown_runtime_and_storage_error_do_not_start_reads(self):
        self.c.settings=replace(self.settings,compatible_runtime_identities={})
        self.policy.tick(self.now);self.assertFalse(self.calls)
        self.c.settings=self.settings;self.c.persistence_error='disk full'
        self.policy.tick(self.now);self.assertFalse(self.calls)

class UiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def panel(self):
        p=MultiTimePanel(AppSettings(schedule_mode='multi',multi_start_times=((8,0),(12,0))))
        self.addCleanup(p.deleteLater)
        return p
    def test_reverting_edit_clears_warning_and_mode_immediately(self):
        p=self.panel();p.editors[0].setTime(QTime(9,0))
        self.assertTrue(p.dirty)
        p.editors[0].setTime(QTime(8,0))
        self.assertFalse(p.dirty);self.assertEqual('',p.save_feedback.text())
        self.assertNotIn('未保存',p.mode_label.text())
    def test_removing_added_row_returns_to_saved_plan(self):
        p=self.panel();p.add_time();self.assertTrue(p.dirty)
        p.remove_time(2)
        self.assertFalse(p.dirty);self.assertEqual('',p.save_feedback.text())
    def test_equivalent_order_and_duplicate_times_do_not_change_schedule(self):
        p=self.panel();p.set_times(((12,0),(8,0),(8,0)),reset_baseline=False);p.mark_dirty()
        self.assertFalse(p.dirty)
    def test_unsaved_rebuild_keeps_original_baseline(self):
        p=self.panel();p.set_times(((9,0),(12,0)),reset_baseline=False);p.mark_dirty()
        self.assertTrue(p.dirty)
        p.editors[0].setTime(QTime(8,0));self.assertFalse(p.dirty)
    def test_failed_auto_sync_preserves_known_quota_and_backs_off(self):
        with tempfile.TemporaryDirectory() as folder:
            prior=state(usage_checked_at=time.time()-600,used_percent=30)
            provider=Provider(prior)
            c=ApplicationController([provider],AppStateStore(Path(folder)/'state.json'))
            c.settings=AppSettings(compatible_runtime_identities={'codex':'r'});c.states={'codex':prior}
            w=MainWindow(c,{'codex':provider},Startup())
            w.usage_sync_timer.stop();w.automation_timer.stop();w.clock_timer.stop()
            w.active_operations['codex']='sync';w._automatic_syncs.add('codex')
            bad=replace(prior,used_percent=None,quota_state='UNKNOWN')
            w._operation_completed('codex',ProviderOperationResult('SYNC_INCONCLUSIVE',bad,False))
            self.assertEqual(prior,c.states['codex'])
            self.assertGreater(w.usage_auto_sync.retry_after,time.time()+290)
            w.active_operations['codex']='sync';w._automatic_syncs.add('codex')
            updated=replace(prior,used_percent=36,usage_checked_at=time.time())
            w._operation_completed('codex',ProviderOperationResult('SYNC_UPDATED',updated,False))
            self.assertEqual(36,c.states['codex'].used_percent)
            self.assertEqual(0,w.usage_auto_sync.retry_after)
            self.assertFalse(w._automatic_syncs)
            w.close();w.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
