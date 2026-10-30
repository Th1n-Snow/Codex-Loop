"""State-driven Chinese UI coverage, including background-produced errors."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import ast,json,re,tempfile,time,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from datetime import datetime
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QLabel,QAbstractButton,QComboBox,QMessageBox,QWidget
from sentinel import zh_cn
from sentinel.app_state import AppSettings,AppStateStore,ProviderViewState
from sentinel.app_controller import ApplicationController
from sentinel.desktop import MainWindow,DesktopShell
from sentinel.presentation import operational_presentation
from sentinel.activity import RecentStartsDialog,START_OUTCOMES
from sentinel.history import SafeHistory
from sentinel.self_test import SelfTestResult,self_test_message
from sentinel.provider_runtime import ProviderOperationResult
from sentinel.update_ui import UpdatePanel
from sentinel.updates import UpdateCheckResult,ReleaseInfo,ReleaseAsset,VerifiedInstaller,ArtifactUnavailableError
from test_local_self_test import Provider,Startup,state

ROOT=Path(__file__).resolve().parents[1]
# Names, executable paths, protocol method identifiers and persisted codes are
# data, not English user instructions. Nothing else is exempted in widgets.
NAMES=r'Codex Loop|Codex|Loop|GitHub|Windows|Linux|OpenAI|MIT|English|Python|Qt|PySide6|Shiboken6|SHA-256|SHA|app-server|read-only|PATH|LOCALAPPDATA|CODEX_HOME|XDG_STATE_HOME'
def leftovers(text):
    text=re.sub(r'<[^>]+>',' ',text)
    text=re.sub(r'https?://[^\s<>]+',' ',text)
    text=re.sub(r'gpt-[A-Za-z0-9_.-]+',' ',text)
    text=re.sub(r'(?:[A-Za-z]:[\\/]|%[A-Z_]+%[\\/]|\$[A-Z_]+[\\/])[^\s<>]+',' ',text)
    text=re.sub(r'account/rateLimits/read|thread/start|turn/start|install\.sh',' ',text)
    text=re.sub(r'(?<![A-Za-z0-9_])(?:'+NAMES+r')(?![A-Za-z0-9_])',' ',text)
    text=re.sub(r'\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b',' ',text)
    text=re.sub(r'\b(?:ANCHORED|UNANCHORED|EXHAUSTED|ABSENT|UNKNOWN|READY|GUARDED|WAITING|ALREADY_ANCHORED|ANCHOR_VERIFIED)\b',' ',text)
    text=re.sub(r'(?<=[（(])v\b',' ',text)
    text=re.sub(r'CodexLoop(?:-Setup)?(?:\.exe)?|\.jsonl?|\.zip|\.exe|\.sha256|\bv\d+(?:\.\d+)+\b',' ',text)
    return re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*",text)

class LocalizationCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([]);zh_cn.install()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=datetime(2026,10,22,12,30).timestamp()
        self.base=state(detail='Codex confirmed this reset time. No Codex traffic is needed for the countdown.',used_percent=47,weekly_used_percent=24,reset_at=int(self.now+3600),last_verified_at=self.now,usage_checked_at=self.now)
        self.good=AppSettings(automation_enabled=True,first_run_complete=True,schedule_mode='multi',compatible_runtime_identities={'codex':'r'},checked_runtime_identities={'codex':'r'},ui_language='zh_CN')
        p=Provider(self.base);self.c=ApplicationController([p],AppStateStore(Path(self.temp.name)/'state.json'));self.c.settings=self.good;self.c.states={'codex':self.base}
        self.w=MainWindow(self.c,{'codex':p},Startup());self.w.evaluate_automation=lambda:None
        class NoTraffic:
            def start(_self,*args):raise AssertionError('Localization review must never start a request')
        self.w.thread_pool=NoTraffic()
        self.w.usage_auto_sync.tick=lambda *args:None
        self.w._maybe_sync_usage=lambda:None
        for timer in self.w.findChildren(QTimer):timer.stop()
        self.w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True);self.w.resize(1120,850);self.w.show();self.app.processEvents()
        self.seen=[]
    def tearDown(self):
        self.w.close();self.w.deleteLater();self.app.processEvents()
        zh_cn.set_language('zh_CN',self.app)
    def assertChinese(self,text,context):
        bad=leftovers(text)
        self.assertFalse(bad,f'{context}: {bad!r} in {text!r}')
    def checkWidgets(self,root,context):
        for obj in [root,*root.findChildren(QWidget)]:
            if obj.isHidden() or not obj.isVisibleTo(root):continue
            if isinstance(obj,(QLabel,QAbstractButton)):
                self.assertChinese(obj.text(),context+'/'+obj.objectName())
            if isinstance(obj,QComboBox):
                for i in range(obj.count()):self.assertChinese(obj.itemText(i),context+'/option')
            for method in ('toolTip','accessibleName','accessibleDescription'):
                text=getattr(obj,method)()
                if text:self.assertChinese(text,context+'/'+method)
        self.seen.append(context)
    def test_all_operational_branches_and_background_details(self):
        b=self.base;g=self.good;n=self.now
        cases=[('active',g,b,None),('local-write-failed',g,b,'state_write_failed'),('paused',replace(g,automation_paused_until=n+3600),b,None),('first-run',AppSettings(),None,None),('no-status',g,None,None),('not-installed',g,replace(b,installed=False),None),('checking',g,replace(b,status='Checking'),None),('first-detected',AppSettings(),replace(b,status='Detected',reset_at=None,last_verified_at=None,usage_checked_at=None),None),('blocked-stopped',g,replace(b,status='Needs attention',detail='The Codex compatibility check stopped safely. No automatic request was sent.'),None),('blocked-failed',g,replace(b,status='Needs attention',detail='The Codex compatibility check failed safely. No automatic request was sent.'),None),('off',replace(g,automation_enabled=False),b,None),('reconnecting',g,replace(b,status='Needs attention',compatibility_next_retry_at=n+60),None),('unverified-runtime',replace(g,compatible_runtime_identities={},checked_runtime_identities={}),b,None),('guarded',g,replace(b,reset_at=None,quota_state='UNANCHORED',last_verified_at=None,outcome_category='GUARDED'),None),('weekly-exhausted',g,replace(b,weekly_used_percent=100),None),('weekly-only',g,replace(b,quota_state='ABSENT',quota_evidence='valid_weekly_only',reset_at=None),None),('weekly-unavailable',g,replace(b,weekly_used_percent=None),None),('quota-unknown',g,replace(b,quota_state='UNKNOWN'),None),('multi-waiting',g,replace(b,reset_at=None,quota_state='UNANCHORED',last_verified_at=None),None),('manual-first-window',replace(g,schedule_mode='daily'),replace(b,quota_state='UNANCHORED',last_verified_at=None),None),('schedule-invalid',replace(g,schedule_mode='invalid'),replace(b,reset_at=int(n-100),quota_state=None,last_verified_at=None),None),('daily-due',replace(g,schedule_mode='daily',daily_start_hour=12,daily_start_minute=0),replace(b,reset_at=int(n-7200),quota_state=None,last_verified_at=n-100),None),('daily-waiting',replace(g,schedule_mode='daily',daily_start_hour=18),replace(b,reset_at=int(n-100),quota_state=None,last_verified_at=n-100),None),('status-unavailable',replace(g,schedule_mode='daily'),replace(b,status='Unavailable',reset_at=None,quota_state=None,last_verified_at=n-100,usage_checked_at=None,detail='No local status yet'),None),('waiting-first',replace(g,schedule_mode='daily'),replace(b,status='Detected',reset_at=None,quota_state=None,last_verified_at=None,usage_checked_at=None),None)]
        cases.append(('weekly-overnight',replace(g,schedule_mode='weekly',weekly_start_times=((13,0),)*7),replace(b,reset_at=int(n-100),quota_state=None,last_verified_at=n-100),None))
        # Every fixed detail produced by the runtime is rendered through the
        # real blocked card, not just looked up in a translation dictionary.
        modules=('provider_runtime.py','providers.py','app_controller.py','chain.py')
        details=set()
        for module in modules:
            tree=ast.parse((ROOT/'src/sentinel'/module).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.match(r'(The |Codex |Provider |Read-only |A request |No |Post-trigger |Weekly |Quota-consuming |Starting |Bootstrap )',node.value) and node.value.endswith('.'):
                    details.add(node.value)
        for i,detail in enumerate(sorted(details)):
            cases.append((f'producer-detail-{i}',g,replace(b,status='Needs attention',detail=detail),None))
        kinds=set();covered=set()
        import sys
        def record_lines(frame,event,arg):
            if event=='line' and frame.f_code.co_name=='operational_presentation':covered.add(frame.f_lineno)
            return record_lines

        for name,settings,value,error in cases:
            with self.subTest(name=name):
                self.c.settings=settings;self.c.persistence_error=error;self.c.states={} if value is None else {'codex':value}
                previous=sys.gettrace();sys.settrace(record_lines)
                try:p=operational_presentation(settings,value,now=n,persistence_error=error)
                finally:sys.settrace(previous)
                kinds.add(p.kind)
                for field in ('banner_title','banner_detail','card_status','card_headline','card_detail','next_action','tray_text'):
                    self.assertChinese(zh_cn.translate(getattr(p,field)),name+'/'+field)
                if value is not None:
                    self.w.refresh_clock(now=n)
                    for page in range(3):
                        self.w.show_page(page);self.app.processEvents();self.checkWidgets(self.w,name+f'/page-{page}')
        out=ROOT/'artifacts/localization';out.mkdir(parents=True,exist_ok=True)
        source=ast.parse((ROOT/'src/sentinel/presentation.py').read_text(encoding='utf-8'))
        branches={node.lineno for node in ast.walk(source) if isinstance(node,ast.Return) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='make'}
        missing=sorted(branches-covered)
        (out/'branches.json').write_text(json.dumps({'total_return_branches':len(branches),'covered':len(branches&covered),'missing':missing}),encoding='utf-8')
        self.assertFalse(missing,f'Uncovered operational presentation branches: {missing}')
        (out/'operational.json').write_text(json.dumps({'cases':len(cases),'kinds':sorted(kinds),'widget_sweeps':len(self.seen),'details':len(details)},ensure_ascii=False,indent=2),encoding='utf-8')
    def test_diagnostic_events_and_notification_messages(self):
        from sentinel.diagnostics import technical_summary
        events=[{'event':'compatibility_incident','phase':phase,'category':'app_server_timeout','occurred_at':self.now} for phase in ('failed','retry','exhausted','recovered')]
        events.append({'event':'compatibility_blocked_start','phase':'blocked_start','category':'app_server_timeout','occurred_at':self.now,'opportunity_at':self.now+60})
        text=technical_summary({'codex':self.base},self.good,app_version='1.1.2',compatibility_events=events)
        self.w.diagnostic_text.setText(text)
        self.assertChinese(self.w.diagnostic_text.text(),'diagnostics/events')
        self.assertIn('app_server_timeout',self.w.diagnostic_text.text())
        for title,body in (
            ('Codex connection needs attention','Read-only retries ended. Automatic starts remain paused.'),
            ('Scheduled start blocked','Codex needs a compatibility check. No start was sent.'),
            ('Codex connection restored','Codex Loop can follow the saved schedule again. Safety checks still apply.')):
            self.assertChinese(zh_cn.translate(title+'\n'+body),'notification')

    def test_disconnection_explains_reason_in_dashboard_and_settings(self):
        raw='The check stopped safely (rate_limits_unavailable). Nothing was retried. See Settings for detail.'
        failed=replace(self.base,status='Needs attention',detail=raw)
        self.c.states={'codex':failed}
        self.w.refresh_clock(now=self.now)
        for page in (0,1):
            self.w.show_page(page);self.app.processEvents();self.checkWidgets(self.w,'disconnected/page-'+str(page))
        self.assertIn('暂时无法读取',self.w.compatibility_status.text())
        self.assertIn('重新检查',self.w.compatibility_status.text())
        self.assertNotIn('兼容性检查通过',self.w.compatibility_status.text())
        p=operational_presentation(self.good,failed,now=self.now)
        for text in (p.banner_detail,p.card_detail):
            self.assertNotIn('rate_limits_unavailable',text)
            self.assertIn('不代表额度已耗尽',zh_cn.translate(text))
        self.assertIn('rate_limits_unavailable',self.w.diagnostic_text.text())
        self.c.states={'codex':self.base};self.w.refresh_clock(now=self.now)
        self.assertIn('兼容性检查通过',self.w.compatibility_status.text())
        from sentinel.diagnostics import connection_issue_detail
        for category in ('app_server_timeout','not_logged_in','runtime_not_found','unknown_future_error'):
            value=replace(failed,detail=f'The check stopped safely ({category}). Nothing was retried. See Settings for detail.')
            detail=connection_issue_detail(value)
            self.assertNotIn(category,detail)
            self.assertChinese(zh_cn.translate(detail),'connection/'+category)

    def test_sync_states_and_long_results(self):
        c=self.w.provider_cards['codex']
        for state_name in ('idle','syncing','updated','inconclusive','unavailable'):
            c.set_sync_state(state_name);self.checkWidgets(c,'sync/'+state_name)

    def test_native_notification_delivery_uses_current_language(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        # Keep the real Qt signal connection, but intercept the final native
        # boundary after connecting. No OS notifications or Codex calls occur.
        with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=False):
            shell=DesktopShell(self.w)
        slot=getattr(shell,'show_notification',shell.tray.showMessage)
        delivered=[]
        pairs=(
            ('Codex connection needs attention','Read-only retries ended. Automatic starts remain paused.',
             'Codex 连接需要处理','只读重连已结束，自动预热仍暂停。'),
            ('Scheduled start blocked','Codex needs a compatibility check. No start was sent.',
             '定时预热未通过检查','需要重新检查 Codex 兼容性，未发送预热请求。'),
            ('Codex connection restored','Codex Loop can follow the saved schedule again. Safety checks still apply.',
             'Codex 连接已恢复','Codex Loop 可以继续按已保存的时间表运行，预热前仍会执行安全检查。'),
            ('Codex connection needs attention','Automatic starts are paused. Recheck Codex when ready.',
             'Codex 连接需要处理','自动预热已暂停，可重新检查 Codex 后继续。'),
        )
        producers=set()
        for node in ast.walk(ast.parse((ROOT/'src/sentinel/desktop.py').read_text(encoding='utf-8'))):
            if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
            args=node.args[1:3] if node.func.attr=='_notify_compatibility' else (
                node.args[:2] if node.func.attr=='emit' and isinstance(node.func.value,ast.Attribute)
                and node.func.value.attr=='notification_requested' else ())
            if len(args)==2 and all(isinstance(a,ast.Constant) and isinstance(a.value,str) for a in args):
                producers.add(tuple(a.value for a in args))
        self.assertEqual(producers,{(p[0],p[1]) for p in pairs},'Notification producer coverage changed')
        try:
            with patch.object(shell.tray,'showMessage',side_effect=lambda *args:delivered.append(args)):
                for language in ('zh_CN','en','zh_CN'):
                    self.w._language_selected(language)
                    for title,body,zh_title,zh_body in pairs:
                        with self.subTest(language=language,title=title,body=body):
                            before=len(delivered)
                            self.w.notification_requested.emit(title,body)
                            self.app.processEvents()
                            self.assertEqual(before+1,len(delivered),'Signal bypassed notification delivery adapter')
                            expected=(zh_title,zh_body) if language=='zh_CN' else (title,body)
                            self.assertEqual(expected,delivered[-1][:2])
                            if language=='zh_CN':
                                self.assertChinese('\n'.join(delivered[-1][:2]),'native-notification')
                # A pending notification uses the language at delivery time.
                title,body,zh_title,zh_body=pairs[0]
                self.w._language_selected('en')
                QTimer.singleShot(0,lambda:self.w.notification_requested.emit(title,body))
                self.w._language_selected('zh_CN')
                self.app.processEvents()
                self.assertEqual((zh_title,zh_body),delivered[-1][:2])
                out=ROOT/'artifacts/localization';out.mkdir(parents=True,exist_ok=True)
                (out/'notifications.json').write_text(json.dumps({'message_pairs':len(pairs),'deliveries':len(delivered),'native_notifications_sent':0}),encoding='utf-8')
        finally:
            self.w.notification_requested.disconnect(slot)
            shell.tray.hide();shell.tray.deleteLater()
    def test_history_all_saved_states_empty_and_corrupt(self):
        h=SafeHistory(Path(self.temp.name)/'history.jsonl')
        d=RecentStartsDialog(h);d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True);d.show();self.app.processEvents();self.checkWidgets(d,'history/empty')
        for i,key in enumerate(START_OUTCOMES):
            a=h.reserve_trigger(mode='rollover',idempotency_key=str(i),boundary_reset_at=None,model='gpt-6-luna',reasoning_effort='low',now=self.now+i*100)
            if key!='reserved':
                h.transition_trigger(a.attempt_id,'launch_attempted',now=self.now+i*100+1)
                if key!='launch_attempted':h.transition_trigger(a.attempt_id,key,now=self.now+i*100+2)
        d.refresh();self.app.processEvents();self.checkWidgets(d,'history/all-six-states')
        h.path.write_text('invalid');d.refresh();self.app.processEvents();self.checkWidgets(d,'history/corrupt');d.close();d.deleteLater()
    def test_self_test_outcomes_and_postcheck_variants(self):
        card=self.w.provider_cards['codex'];count=0
        before_states=(self.base,replace(self.base,quota_state='UNANCHORED'),None)
        after_states=(self.base,replace(self.base,reset_at=self.base.reset_at+200),replace(self.base,quota_state='UNKNOWN'),None)
        for outcome in ('turn_completed','turn_failed','turn_timeout','turn_stream_unavailable','request_unconfirmed','connection_failed','precheck_failed','precheck_blocked'):
            for before in before_states:
                for after in after_states:
                    for cleanup in (True,False):
                        r=SelfTestResult(outcome,ProviderOperationResult('SYNC_UPDATED',before,False) if before else None,ProviderOperationResult('SYNC_UPDATED',after,False) if after else None,'gpt-6-luna',outcome not in ('connection_failed','precheck_failed','precheck_blocked'),cleanup,'ephemeral')
                        text,tone=self_test_message(r);card.show_verification_result(text,tone);self.assertChinese(card.verification_label.text(),'self-test/'+outcome);count+=1
        (ROOT/'artifacts/localization/self-tests.json').write_text(json.dumps({'cases':count}),encoding='utf-8')
    def test_update_states_errors_and_confirmations(self):
        panel=self.w.update_panel
        release=ReleaseInfo('9.0.0',('修复兼容性提示。',),'https://github.com/Th1n-Snow/Codex-Loop/releases/tag/v9.0.0',ReleaseAsset('CodexLoop-Setup.exe','https://github.com/a.exe'),ReleaseAsset('CodexLoop-Setup.exe.sha256','https://github.com/a.sha256'))
        for key in ('no_release','latest','no_artifact','update_available'):
            panel._operation_completed('check',UpdateCheckResult(key,release if key=='update_available' else None,ArtifactUnavailableError('9.0.0',release.page_url,'Windows installer') if key=='no_artifact' else None))
            self.w.show_page(1);self.app.processEvents();self.checkWidgets(panel,'updates/'+key)
        panel._operation_completed('download',VerifiedInstaller(Path(self.temp.name)/'CodexLoop-Setup.exe','a'*64));self.checkWidgets(panel,'updates/downloaded')
        for key,text in (('checking','Checking GitHub…'),('downloading','Downloading and verifying the Windows installer…')):
            panel._set_busy(key,text);self.checkWidgets(panel,'updates/'+key)
        # Exercise real variable error text, including filenames and HTTP codes.
        for message in ('GitHub replied with an error (403). Try again later.','The Windows installer checksum did not match the release.','The release included duplicate CodexLoop-Setup.exe files.','The install confirmation could not be opened. Try again.'):
            panel._operation_failed('check',message);self.checkWidgets(panel,'updates/error/'+message)
        import ast
        for module in ('updates.py','update_ui.py'):
            tree=ast.parse((ROOT/'src/sentinel'/module).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node,ast.JoinedStr):continue
                plain=''.join(v.value for v in node.values if isinstance(v,ast.Constant))
                if len(re.findall('[A-Za-z]+',plain))<2 or plain.startswith('(') or r'\s' in plain:continue
                values={'artifact.description':'Windows installer','description':'Windows installer','version':'9.0.0','release.version':'9.0.0','self.platform_name':'Windows','PRODUCT.display_name':'Codex Loop','PRODUCT.version':'1.1.2','name':'CodexLoop-Setup.exe','exc.code':'403'}
                message=''.join(v.value if isinstance(v,ast.Constant) else str(values.get(ast.unparse(v.value),'9.0.0')) for v in node.values)
                panel._operation_failed('check',message);self.checkWidgets(panel,'updates/template/'+message)
        from types import SimpleNamespace
        isolated=UpdatePanel(platform_name='Windows',confirm_install=lambda version:True)
        isolated.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True);isolated.show()
        isolated.release=release;isolated.installer=VerifiedInstaller(Path(self.temp.name)/'CodexLoop-Setup.exe','a'*64)
        isolated.updater=SimpleNamespace(launch_installer=lambda installer:None)
        isolated.start_install();self.app.processEvents();self.checkWidgets(isolated,'updates/installer-started')
        isolated.close();isolated.deleteLater()
        panel._checking_model_support=True;panel._operation_completed('check',UpdateCheckResult('latest'));self.checkWidgets(panel,'updates/latest-model-support')
        (ROOT/'artifacts/localization/updates.json').write_text(json.dumps({'widget_scenarios':len(self.seen),'confirmations':3}),encoding='utf-8')
        captured=[]
        def dismiss():
            box=QApplication.activeModalWidget()
            if isinstance(box,QMessageBox):
                try:self.assertChinese(box.windowTitle()+'\n'+box.text(),'confirmation');captured.append(box.text())
                finally:box.done(QMessageBox.StandardButton.Cancel)
        for invoke in (self.w._confirm_enable,self.w._confirm_bootstrap,lambda:panel._confirm_install('9.0.0')):
            QTimer.singleShot(20,dismiss);self.assertFalse(invoke())
        self.assertEqual(3,len(captured))
    def test_tray_controls_and_language_roundtrip(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=False):shell=DesktopShell(self.w)
        try:
            for name,settings,value in (
                ('active',self.good,self.base),
                ('paused',replace(self.good,automation_paused_until=self.now+3600),self.base),
                ('off',replace(self.good,automation_enabled=False),self.base),
                ('blocked',self.good,replace(self.base,status='Needs attention',detail='The Codex compatibility check stopped safely. No automatic request was sent.'))):
                self.c.settings=settings;self.c.states={'codex':value};self.w.refresh_clock(now=self.now);shell.refresh_menu(now=self.now)
                self.assertChinese(shell.tray.toolTip(),'tray/'+name)
                for action in shell.tray.contextMenu().actions():self.assertChinese(action.text(),'tray/action/'+name)
            self.w.update_panel.release=ReleaseInfo('9.0.0',('Fixed a newly discovered bug.',),'https://github.com/a',ReleaseAsset('a','https://github.com/a'),ReleaseAsset('b','https://github.com/b'))
            self.w.update_panel.refresh_localized_release_notes()
            self.assertChinese(self.w.update_panel.notes_label.text(),'external-release-notes')
            self.w._language_selected('en')
            self.assertIn('Fixed a newly discovered bug.',self.w.update_panel.notes_label.text())
            self.w._language_selected('zh_CN')
            for page in range(3):
                self.w.show_page(page);self.app.processEvents();self.checkWidgets(self.w,'roundtrip/page-'+str(page))
        finally:shell.tray.hide();shell.tray.deleteLater()

    def test_known_ui_and_runtime_source_messages_have_no_untranslated_prose(self):
        modules=('desktop.py','appearance.py','ui_components.py','multi_time_ui.py','update_ui.py','updates.py','presentation.py','providers.py','provider_runtime.py','app_controller.py','self_test.py','diagnostics.py','chain.py','activity.py','appointments.py')
        excluded={'h:mm AP','QLineEdit { border: none; background: transparent; border-radius: 0px; }','ArtifactUnavailableError | None','Codex Loop: state_write_failed'}
        checked=set();failures=[]
        for name in modules:
            tree=ast.parse((ROOT/'src/sentinel'/name).read_text(encoding='utf-8'))
            docs={id(n.body[0].value) for n in ast.walk(tree) if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant)}
            for n in ast.walk(tree):
                if not isinstance(n,ast.Constant) or not isinstance(n.value,str) or id(n) in docs:continue
                text=n.value
                if text in excluded or text == r'The check stopped safely \(([^)]+)\)' or text.startswith(('%','http','QLineEdit','QPushButton')) or len(text)>2000:continue
                if len(re.findall(r'[A-Za-z]+',text))<2 or not (' ' in text or '\n' in text):continue
                if '::' in text or r'\d' in text or 'return ' in text:continue
                translated=zh_cn.translate(text);checked.add((name,n.lineno,text))
                if leftovers(translated):failures.append((name,n.lineno,text,translated,leftovers(translated)))
        self.assertFalse(failures,json.dumps(failures,ensure_ascii=False,indent=2))
        out=ROOT/'artifacts/localization';out.mkdir(parents=True,exist_ok=True)
        (out/'catalog.json').write_text(json.dumps({'source_message_checks':len(checked),'untranslated':0}),encoding='utf-8')

if __name__=='__main__':unittest.main()
