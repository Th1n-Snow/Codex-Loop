import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,tempfile,json
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from sentinel.app_state import AppSettings,AppStateStore
from sentinel.app_controller import ApplicationController
from sentinel.desktop import MainWindow
from sentinel.ui_theme import TOKENS,select_theme
from sentinel import zh_cn
from test_local_self_test import Provider,Startup,state

class DisplayPreferencesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        zh_cn.install()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        provider=Provider(state())
        self.c=ApplicationController([provider],AppStateStore(Path(self.tmp.name)/'state.json'))
        self.c.settings=AppSettings(theme_mode='dark',ui_language='zh_CN')
        self.c.states={'codex':provider.state}
        self.w=MainWindow(self.c,{'codex':provider},Startup())
        self.w.evaluate_automation=lambda:None
    def tearDown(self):
        self.w.close();self.w.deleteLater();self.app.processEvents()
        zh_cn.set_language('zh_CN',self.app);select_theme(False)
    def test_preferences_roundtrip_and_missing_fields_default_safely(self):
        self.c.set_display_preferences(theme_mode='light',ui_language='en')
        saved=self.c.store.load()
        self.assertEqual(('light','en'),(saved.theme_mode,saved.ui_language))
        self.c.store.path.write_text(json.dumps({'settings':{'theme_mode':[], 'ui_language':{}}}))
        saved=self.c.store.load()
        self.assertEqual(('system','zh_CN'),(saved.theme_mode,saved.ui_language))
    def test_user_can_switch_theme_without_saving_draft_or_starting_worker(self):
        panel=self.w.multi_time_panel
        panel.editors[0].setTime(QTime(9,17));draft=panel.values()
        before=self.c.settings.multi_start_times
        self.w.appearance_panel.theme_buttons['light'].click()
        self.assertEqual('#F5F7F5',TOKENS.background)
        self.assertEqual('light',self.c.store.load().theme_mode)
        self.assertTrue(panel.dirty);self.assertEqual(draft,panel.values())
        self.assertEqual(before,self.c.settings.multi_start_times)
        self.assertFalse(self.w.active_operations)
        self.w.appearance_panel.theme_buttons['dark'].click()
        self.assertEqual('#0A111C',TOKENS.background)
    def test_languages_roundtrip_and_dynamic_quota_text_is_english(self):
        combo=self.w.appearance_panel.language_combo
        combo.setCurrentIndex(combo.findData('en'))
        self.assertEqual('en',self.c.store.load().ui_language)
        self.w.refresh_clock()
        self.assertIn('Usage refreshes automatically',self.w.provider_cards['codex'].sync_button.toolTip())
        self.assertEqual('Save and use these times',self.w.multi_time_panel.save_button.text())
        self.assertEqual('Warm-up self-test',self.w.provider_cards['codex'].verify_button.text())
        self.assertIn('System',[button.text() for button in self.w.appearance_panel.theme_buttons.values()])
        self.w.multi_time_panel.editors[0].setTime(QTime(10,22))
        self.assertIn('Unsaved',self.w.multi_time_panel.save_feedback.text())
        self.w.refresh_clock()
        combo.setCurrentIndex(combo.findData('zh_CN'))
        self.assertEqual('保存并使用这些时间',self.w.multi_time_panel.save_button.text())
        self.assertEqual('预热自检',self.w.provider_cards['codex'].verify_button.text())
        self.w.refresh_clock()
        self.assertIn('仪表盘约每分钟一次',self.w.provider_cards['codex'].sync_button.toolTip())
        self.assertNotIn('Usage refreshes automatically',self.w.provider_cards['codex'].sync_button.toolTip())
        self.assertTrue(self.w.multi_time_panel.dirty)
    def test_system_changes_only_apply_when_following_system(self):
        with patch('sentinel.appearance.system_is_light',return_value=True):
            self.w._theme_selected('system')
            self.assertEqual('#F5F7F5',TOKENS.background)
        with patch('sentinel.appearance.system_is_light',return_value=False):
            self.w.appearance_manager._system_changed()
            self.assertEqual('#0A111C',TOKENS.background)
        with patch('sentinel.appearance.system_is_light',return_value=True):
            self.w._theme_selected('dark');self.w.appearance_manager._system_changed()
            self.assertEqual('#0A111C',TOKENS.background)
    def test_save_failure_rolls_back_control_and_does_not_change_theme(self):
        with patch.object(self.c,'set_display_preferences',return_value=False):
            self.w.appearance_panel.theme_buttons['light'].click()
        self.assertTrue(self.w.appearance_panel.theme_buttons['dark'].isChecked())
        self.assertEqual('#0A111C',TOKENS.background)
    def test_item_ids_and_model_strings_are_never_translated(self):
        combo=self.w.appearance_panel.language_combo
        self.assertEqual('zh_CN',combo.itemData(0));self.assertEqual('en',combo.itemData(1))
        label=QLabel('使用模型：gpt-6-luna。')
        zh_cn.set_language('en',self.app)
        self.assertEqual('Model: gpt-6-luna。',label.text())
        self.assertEqual('zh_CN',combo.itemData(0))
        label.deleteLater()

    def test_peach_theme_persists_and_switching_preserves_schedule_draft(self):
        self.w.multi_time_panel.editors[0].setTime(QTime(9,17))
        draft=self.w.multi_time_panel.values()
        schedule=self.c.settings.multi_start_times
        self.w.appearance_panel.color_buttons['peach'].click()
        self.assertEqual('peach',self.c.store.load().color_theme)
        self.assertEqual('#17181C',TOKENS.background)
        self.w.appearance_panel.theme_buttons['light'].click()
        self.assertEqual('#FEF5F9',TOKENS.background)
        self.assertEqual('#CD6588',TOKENS.progress_fill)
        self.assertEqual('#FCD9E1',TOKENS.progress_track)
        self.assertEqual(schedule,self.c.settings.multi_start_times)
        self.assertEqual(draft,self.w.multi_time_panel.values())
        self.assertTrue(self.w.multi_time_panel.dirty)
        self.assertFalse(self.w.active_operations)
        from sentinel.appearance import AppearanceManager
        from PySide6.QtWidgets import QWidget
        restored=QWidget()
        manager=AppearanceManager(restored,self.c.store.load())
        manager.apply_theme('light')
        self.assertEqual('#FEF5F9',TOKENS.background)
        restored.deleteLater()
        self.w.appearance_panel.color_buttons['classic'].click()
        self.assertEqual('#F5F7F5',TOKENS.background)
        self.assertIsNone(TOKENS.progress_fill)

    def test_peach_system_theme_and_failed_save(self):
        self.w._color_theme_selected('peach')
        with patch('sentinel.appearance.system_is_light',return_value=True):
            self.w._theme_selected('system')
            self.assertEqual('#FEF5F9',TOKENS.background)
        with patch('sentinel.appearance.system_is_light',return_value=False):
            self.w.appearance_manager._system_changed()
            self.assertEqual('#17181C',TOKENS.background)
        with patch.object(self.c,'set_display_preferences',return_value=False):
            self.w.appearance_panel.color_buttons['classic'].click()
        self.assertTrue(self.w.appearance_panel.color_buttons['peach'].isChecked())
        self.assertEqual('#17181C',TOKENS.background)
        self.c.store.path.write_text(json.dumps({'settings':{'color_theme':[]}}))
        self.assertEqual('classic',self.c.store.load().color_theme)

    def test_simplified_automation_card_retains_history_and_switch(self):
        card=self.w.schedule_card
        self.assertFalse(hasattr(card,'pause_button'))
        self.assertFalse(hasattr(card,'manage_button'))
        self.assertEqual('最近预热记录',card.history_button.text())
        self.assertIs(self.w.dashboard_automation_toggle,card.automation_toggle)
        self.w._language_selected('en')
        self.assertEqual('Peach blossom',self.w.appearance_panel.color_buttons['peach'].text())
        self.w._language_selected('zh_CN')
        self.assertEqual('桃夭',self.w.appearance_panel.color_buttons['peach'].text())

    def test_enable_confirmation_body_translates_with_real_paragraph_breaks(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QMessageBox
        for language in ('zh_CN','en'):
            self.w._language_selected(language)
            seen=[]
            def inspect():
                dialog=QApplication.activeModalWidget()
                if isinstance(dialog,QMessageBox):
                    seen.append((dialog.windowTitle(),dialog.text()))
                    dialog.done(QMessageBox.StandardButton.Cancel)
            QTimer.singleShot(20,inspect)
            self.assertFalse(self.w._confirm_enable())
            self.assertEqual(1,len(seen))
            title,body=seen[0]
            self.assertIn('\n\n',body)
            if language=='zh_CN':
                self.assertEqual('开启自动预热？',title)
                self.assertIn('检查每周剩余额度',body)
                self.assertNotIn('will use your signed-in',body)
            else:
                self.assertIn('will use your signed-in',body)
