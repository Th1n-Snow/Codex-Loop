from dataclasses import dataclass
from datetime import datetime
from .provider_runtime import ProviderOperationResult
from .trigger import AppServerTrigger, TriggerConfig, dedicated_trigger_workspace

@dataclass(frozen=True)
class SelfTestResult:
    outcome: str
    before: ProviderOperationResult | None = None
    after: ProviderOperationResult | None = None
    model: str = ''
    request_possibly_sent: bool = False
    cleanup_ok: bool = True
    thread_id: str | None = None


def run_self_test(runner, runtime_identity: str) -> SelfTestResult:
    # Manual one-shot only. Never call the scheduled chain or retry a turn.
    try:
        before = runner.sync(runtime_identity)
    except Exception:
        return SelfTestResult('precheck_failed')
    if (before.outcome != 'SYNC_UPDATED'
            or before.state.quota_state not in {'ANCHORED','UNANCHORED'}
            or before.state.weekly_used_percent is None
            or before.state.weekly_used_percent >= 100):
        return SelfTestResult('precheck_blocked', before=before)
    session = None
    model = ''
    sent = False
    outcome = 'connection_failed'
    cleanup_ok = True
    thread_id = None
    try:
        session = runner._session_factory()
        trigger = AppServerTrigger(session.client, dedicated_trigger_workspace(runner.history.path),
                                   TriggerConfig(), clock=runner._clock)
        model = trigger.describe().model
        # Set before entering run: an unexpected exception must never imply no send.
        sent = True
        result = trigger.run()
        outcome = result.terminal_outcome
        sent = result.request_possibly_sent
        thread_id = getattr(trigger, 'last_thread_id', None)
    except Exception:
        outcome = 'request_unconfirmed' if sent else 'connection_failed'
    finally:
        if session is not None:
            try: session.close()
            except Exception: cleanup_ok = False
    after = None
    if sent:
        try: after = runner.sync(runtime_identity)
        except Exception: pass
    return SelfTestResult(outcome, before, after, model, sent, cleanup_ok, thread_id)


def self_test_message(result: SelfTestResult) -> tuple[str,str]:
    success = result.outcome == 'turn_completed'
    if success:
        lines = ['自检成功：Codex 已实际完成一次极小请求，预热请求链路可用。', f'使用模型：{result.model}。']
    elif result.outcome in {'precheck_failed','precheck_blocked'}:
        lines = ['自检未发送请求：额度读取失败、额度不足或当前账号不满足测试条件。']
    elif result.request_possibly_sent:
        lines = ['自检未通过：请求可能已发送，但未确认正常完成。不会自动重试，请稍后手动检查。']
    else:
        lines = ['自检失败：连接、模型选择或请求准备未完成，没有发出模型请求。']
    after = result.after
    if after and after.outcome == 'SYNC_UPDATED' and after.state.quota_state == 'ANCHORED':
        reset = after.state.reset_at
        label = datetime.fromtimestamp(reset).strftime('%m-%d %H:%M') if reset else '未知'
        before = result.before.state if result.before else None
        if before and before.quota_state == 'ANCHORED':
            if before.reset_at and reset and abs(before.reset_at-reset) <= 5:
                lines.append(f'当前仍是同一轮窗口，重置时间 {label}；本次测试没有新开一轮。')
            else:
                lines.append(f'当前已确认固定重置时间 {label}；不能单凭本次请求确定新窗口的归因。')
        elif success and before and before.quota_state == 'UNANCHORED':
            lines.append(f'请求前未形成固定倒计时，请求后已确认五小时窗口，重置时间 {label}。')
        else:
            lines.append(f'当前固定重置时间 {label}；请求是否成功以以上完成结果为准。')
    elif result.request_possibly_sent:
        lines.append('请求后的窗口状态尚未确认；不影响上方实际请求完成与否的判定。')
    if result.cleanup_ok:
        if result.thread_id:
            lines.append('测试使用临时会话，连接已关闭，不保存测试聊天，无需归档。')
    else:
        lines.append('临时会话连接未能正常关闭，请检查 Codex Loop 后台进程。')
    return '\n'.join(lines), 'success' if success and result.cleanup_ok else 'warning'
