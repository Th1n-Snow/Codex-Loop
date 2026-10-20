from dataclasses import replace
import unittest
from test_protocol import MemoryTransport, messages
from sentinel.protocol import AppServerClient
from sentinel.app_state import AppSettings, ProviderViewState, automation_decision
from sentinel.presentation import operational_presentation
from sentinel.providers import CodexProvider
from sentinel.provider_runtime import ProviderOperationResult

class WarmupReconnectRegressionTests(unittest.TestCase):
    def client(self, incoming):
        transport=MemoryTransport([messages()['initialize_result'],*incoming])
        client=AppServerClient(transport,client_version='1.3.8')
        client.initialize()
        return client,transport

    def test_retry_notifications_do_not_abort_wait_or_send_another_turn(self):
        client,transport=self.client([
            {'method':'error','params':{'willRetry':True}},
            {'method':'error','params':{'willRetry':True}},
            {'method':'turn/completed','params':{'turn':{'status':'completed'}}},
        ])
        self.assertEqual('turn_completed',client.await_turn_end(timeout=5))
        self.assertFalse(any(row.get('method')=='turn/start' for row in transport.sent))

    def test_retry_before_submission_response_is_not_buffered_as_failure(self):
        client,_=self.client([
            {'method':'error','params':{'willRetry':True}},
            {'id':2,'result':{'turn':{'id':'turn-1'}}},
            {'method':'turn/completed','params':{'turn':{'status':'completed'}}},
        ])
        client.start_turn({'threadId':'t-1','input':[]})
        self.assertEqual('turn_completed',client.await_turn_end(timeout=5))

    def test_explicit_terminal_status_is_respected(self):
        for status,expected in [('failed','turn_failed'),('interrupted','turn_interrupted'),(None,'turn_unconfirmed')]:
            with self.subTest(status=status):
                client,_=self.client([{'method':'turn/completed','params':{'turn':{'status':status}}}])
                self.assertEqual(expected,client.await_turn_end(timeout=5))

    def test_nonretryable_error_still_stops_wait(self):
        client,_=self.client([{'method':'error','params':{'willRetry':False}}])
        self.assertEqual('turn_error',client.await_turn_end(timeout=5))

class SupersededGuardRegressionTests(unittest.TestCase):
    def settings(self):
        return AppSettings(automation_enabled=True,compatible_runtime_identities={'codex':'r'},checked_runtime_identities={'codex':'r'})
    def state(self):
        return ProviderViewState('codex','Codex',True,True,'Ready','fixed reset',runtime_identity='r',reset_at=20000,last_verified_at=1000,usage_checked_at=1000,weekly_used_percent=16,quota_state='ANCHORED',last_action='ATTEMPT_ALREADY_RECORDED')

    def test_current_verified_window_is_not_hidden_by_old_failed_attempt(self):
        p=operational_presentation(self.settings(),self.state(),now=1100)
        self.assertEqual('active_window',p.kind)
        self.assertIn('下次定时检查',p.next_action)

    def test_unanchored_request_remains_guarded(self):
        state=replace(self.state(),status='Guarded',quota_state='UNANCHORED',outcome_category='GUARDED')
        self.assertEqual('guarded',operational_presentation(self.settings(),state,now=1100).kind)

    def test_readonly_sync_clears_stale_action_without_rewriting_attempt_history(self):
        observed=replace(self.state(),usage_checked_at=1200,last_verified_at=1200,last_action=None)
        class Runner:
            def sync(self,identity):
                return ProviderOperationResult('SYNC_UPDATED',observed,False)
        provider=CodexProvider(operation_runner=Runner())
        result=provider.sync_usage(current_state=self.state())
        self.assertIsNone(result.state.last_action)
        self.assertIsNone(result.state.outcome_category)
        self.assertEqual(20000,result.state.reset_at)
        self.assertEqual('WAIT',automation_decision(True,result.state,now=1300,compatible_runtime_identity='r',checked_runtime_identity='r').action)
        self.assertEqual('WAIT',automation_decision(True,result.state,now=20061,compatible_runtime_identity='r',checked_runtime_identity='r').action)
