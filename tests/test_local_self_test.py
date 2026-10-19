import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from PySide6.QtWidgets import QApplication
from sentinel.app_state import AppSettings,AppStateStore,ProviderViewState
from sentinel.app_controller import ApplicationController
from sentinel.desktop import MainWindow
from sentinel.schedule import MULTI
from sentinel.provider_runtime import ProviderOperationResult
from sentinel.self_test import SelfTestResult,run_self_test,self_test_message
from sentinel.history import SafeHistory
from test_provider_runtime import FakeClient,FakeSession,payload


def state(**values):
    base=ProviderViewState('codex','Codex',True,True,'Ready','fixed',runtime_identity='r',reset_at=int(time.time()+3600),last_verified_at=time.time(),weekly_used_percent=20,quota_state='ANCHORED')
    return replace(base,**values)
def sync(s):return ProviderOperationResult('SYNC_UPDATED',s,False)

class Runner:
    def __init__(self,path,*,before=None,fail_after=False,outcome='turn_completed'):
        self.history=SafeHistory(path);self.calls=0;self.before=before or sync(state());self.fail_after=fail_after
        self.client=FakeClient([payload(18000)]);self.params=None
        original=self.client.start_thread
        def start(params):self.params=params;return original(params)
        self.client.start_thread=start
        self.client.await_turn_end=lambda **kw:outcome
        self.session=FakeSession(self.client)
        self._session_factory=lambda:self.session
        self._clock=time.time
    def sync(self,identity):
        self.calls+=1
        if self.calls>1 and self.fail_after:raise OSError('offline')
        return self.before

class SelfTestTests(unittest.TestCase):
    def run_case(self,**kwargs):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        runner=Runner(Path(folder.name)/'history.jsonl',**kwargs)
        return runner,run_self_test(runner,'r')
    def test_active_window_sends_exactly_one_ephemeral_turn_then_closes(self):
        runner,result=self.run_case()
        self.assertEqual(1,runner.client.turn_calls)
        self.assertTrue(runner.params['ephemeral'])
        self.assertEqual('read-only',runner.params['sandbox'])
        self.assertTrue(runner.session.closed)
        self.assertEqual(2,runner.calls)
        self.assertIn('同一轮',self_test_message(result)[0])
        self.assertIn('自检成功',self_test_message(result)[0])
    def test_unsafe_preflight_sends_nothing(self):
        for quota in ['EXHAUSTED','UNKNOWN','ABSENT']:
            with self.subTest(quota=quota):
                runner,result=self.run_case(before=sync(state(quota_state=quota)))
                self.assertEqual(0,runner.client.turn_calls)
                self.assertEqual('precheck_blocked',result.outcome)
        runner,result=self.run_case(before=sync(state(weekly_used_percent=100)))
        self.assertEqual(0,runner.client.turn_calls)
    def test_request_completion_survives_postcheck_failure(self):
        runner,result=self.run_case(fail_after=True)
        text,tone=self_test_message(result)
        self.assertEqual('success',tone)
        self.assertIn('自检成功',text)
        self.assertIn('窗口状态尚未确认',text)
        self.assertTrue(runner.session.closed)
    def test_failed_or_unknown_turn_never_claims_success_or_retries(self):
        for outcome in ['turn_failed','turn_timeout','turn_stream_unavailable']:
            with self.subTest(outcome=outcome):
                runner,result=self.run_case(outcome=outcome)
                self.assertEqual(1,runner.client.turn_calls)
                self.assertEqual('warning',self_test_message(result)[1])
                self.assertNotIn('自检成功',self_test_message(result)[0])
                self.assertTrue(runner.session.closed)
    def test_missing_model_closes_without_sending(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=Runner(Path(folder)/'history.jsonl');runner.client.model=False
            result=run_self_test(runner,'r')
            self.assertFalse(result.request_possibly_sent)
            self.assertEqual(0,runner.client.turn_calls)
            self.assertTrue(runner.session.closed)
    def test_new_window_claim_requires_unanchored_precheck_and_completion(self):
        result=SelfTestResult('turn_completed',sync(state(quota_state='UNANCHORED')),sync(state()),'test',True)
        self.assertIn('请求后已确认五小时窗口',self_test_message(result)[0])
        self.assertNotIn('请求后已确认五小时窗口',self_test_message(replace(result,outcome='turn_failed'))[0])

class Provider:
    provider_id='codex'
    def __init__(self,state):self.state=state;self.calls=0;self.fail=False
    def detect(self):return self.state
    def self_test(self,*,current_state):
        self.calls+=1
        if self.fail:raise OSError('offline')
        return SelfTestResult('turn_completed',sync(current_state),sync(current_state),'test',True,True,'ephemeral')
    def sync_usage(self,**kwargs):raise AssertionError('Button must exercise actual request runner')
class Startup:
    def is_enabled(self):return False
    def set_enabled(self,value):pass
class Pool:
    def __init__(self):self.workers=[]
    def start(self,w):self.workers.append(w)

class ButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_button_blocks_duplicate_clicks_and_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            current=state();provider=Provider(current)
            controller=ApplicationController([provider],AppStateStore(Path(folder)/'state.json'))
            controller.settings=AppSettings(automation_enabled=True,schedule_mode=MULTI)
            controller.states={'codex':current}
            window=MainWindow(controller,{'codex':provider},Startup());window.evaluate_automation=lambda:None
            pool=Pool();window.thread_pool=pool
            card=window.provider_cards['codex']
            self.assertEqual('预热自检',card.verify_button.text())
            card.verify_button.click();window.start_window_verification('codex')
            self.assertEqual(len(pool.workers),1)
            self.assertFalse(card.verify_button.isEnabled())
            self.assertFalse(card.sync_button.isEnabled())
            pool.workers.pop().run()
            self.assertEqual(provider.calls,1)
            self.assertIn('自检成功',card.verification_label.text())
            self.assertTrue(card.verify_button.isEnabled())
            provider.fail=True;card.verify_button.click();pool.workers.pop().run()
            self.assertIn('自检异常',card.verification_label.text())
            self.assertFalse(window.active_operations)
            self.assertTrue(card.verify_button.isEnabled())
            window.close()
