import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys,time,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest import mock
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication,QComboBox,QLabel
from sentinel.app_state import AppSettings,AppStateStore,ProviderViewState
from sentinel.app_controller import ApplicationController
from sentinel.desktop import MainWindow
from sentinel.schedule import MULTI
from sentinel.multi_time_ui import MultiTimePanel

class Provider:
    provider_id='codex'
    def __init__(self,state):self.state=state
    def detect(self):return self.state
class Startup:
    def is_enabled(self):return False
    def set_enabled(self,value):pass

class SaveFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_feedback_distinguishes_enabled_off_and_paused(self):
        settings=AppSettings(automation_enabled=True,schedule_mode=MULTI)
        panel=MultiTimePanel(settings)
        panel.show_save_success(settings)
        self.assertIn('已生效',panel.save_feedback.text())
        self.assertEqual('✓ 已保存',panel.save_button.text())
        panel.show_save_success(replace(settings,automation_enabled=False))
        self.assertIn('尚未开启',panel.save_feedback.text())
        self.assertNotIn('已生效',panel.save_feedback.text())
        panel.show_save_success(replace(settings,automation_paused_until=time.time()+3600))
        self.assertIn('暂停中',panel.save_feedback.text())
        panel.deleteLater()

    def test_editing_replaces_success_with_unsaved_message(self):
        settings=AppSettings(automation_enabled=True,schedule_mode=MULTI)
        panel=MultiTimePanel(settings)
        panel.show_save_success(settings)
        panel.editors[0].setTime(QTime(13,2))
        self.assertTrue(panel.dirty)
        self.assertIn('未保存',panel.save_feedback.text())
        self.assertFalse(panel.feedback_timer.isActive())
        panel.deleteLater()

    def test_settings_schedule_module_is_removed_and_save_is_confirmed(self):
        with tempfile.TemporaryDirectory() as folder:
            state=ProviderViewState('codex','Codex',True,True,'Ready','fixed',runtime_identity='r',reset_at=int(time.time()+3600),last_verified_at=time.time(),usage_checked_at=time.time(),used_percent=3,weekly_used_percent=16,quota_state='ANCHORED')
            provider=Provider(state)
            controller=ApplicationController([provider],AppStateStore(Path(folder)/'state.json'))
            controller.settings=AppSettings(automation_enabled=True,schedule_mode=MULTI)
            controller.states={'codex':state}
            window=MainWindow(controller,{'codex':provider},Startup())
            window.evaluate_automation=lambda:None
            self.assertEqual([window.appearance_panel.language_combo],window.pages.widget(1).findChildren(QComboBox))
            self.assertFalse(hasattr(window,'daily_time_row'))
            self.assertFalse(hasattr(window,'weekly_schedule_panel'))
            window._save_multi_times(((12,0),(19,1),(22,2)))
            self.assertIn('保存成功',window.multi_time_panel.save_feedback.text())
            self.assertEqual(((12,0),(19,1),(22,2)),controller.store.load().multi_start_times)
            before=controller.settings
            with mock.patch.object(controller,'set_multi_start_times',return_value=False),mock.patch.object(window,'_show_persistence_warning'):
                window._save_multi_times(((15,0),))
            self.assertIn('保存失败',window.multi_time_panel.save_feedback.text())
            self.assertEqual(before,controller.settings)
            window.close()
