"""Additional translations for the local Codex Loop features."""
PAIRS = '''
额度会自动同步：仪表盘约每分钟一次，后台约每五分钟一次；预热任务优先。点击可立即同步。|Usage refreshes automatically: about every minute on the dashboard and every five minutes in the background. Warm-ups take priority. Click to sync now.
外观与语言|Appearance and language
配色方案|Color scheme
跟随系统|System
浅色|Light
深色|Dark
语言|Language
更改立即生效，并保存在本机。|Changes apply immediately and are saved on this computer.
已保存|Saved
设置保存失败，已恢复原来的选择。|Could not save the setting. Your previous selection has been restored.
每天多个时间|Daily time slots
每天按设定时间执行预热检查；电脑休眠时错过的时间点不会集中补发。|Check warm-up at these times each day. Missed slots while the PC sleeps are not replayed in a batch.
＋ 添加时间|+ Add time
保存并使用这些时间|Save and use these times
有未保存的修改，点击保存后才会应用。|Unsaved changes. Save to apply them.
有未保存的修改|Unsaved changes
✓ 已保存|✓ Saved
✓ 保存成功。自动预热尚未开启，打开开关后生效。|✓ Saved. Turn on automatic warm-up to use this schedule.
✓ 保存成功，已选用此时间表；自动预热目前暂停中。|✓ Saved and selected. Automatic warm-up is currently paused.
✓ 保存成功，时间表已生效。|✓ Saved. This schedule is now active.
自动预热已关闭，时间表已保存。|Automatic warm-up is off. Your schedule has been saved.
删除|Remove
添加预热时间|Add a warm-up time
请至少添加一个时间；要停止自动预热，可关闭仪表盘上的自动预热开关。|Add at least one time. To stop automatic warm-up, turn off its switch on the dashboard.
编辑时间后，点击“保存并使用这些时间”切换到此计划。|Edit the times, then select Save and use these times to activate this schedule.
计划已暂停，恢复后继续按时间表运行。|The schedule is paused. It will resume when you turn it back on.
正在使用此计划|Schedule active
尚未选用此计划|Schedule inactive
已到设定时间，正在等待检查。|A scheduled time is due. Waiting for a check.
请添加预热时间。|Add a warm-up time.
预热自检|Warm-up self-test
发送一次极小请求验证实际预热链路，消耗少量额度；使用临时会话，不保存测试聊天。|Send one tiny request to test the warm-up path. Uses a small amount of quota and an ephemeral chat that is not saved.
会消耗少量额度，约需 1–5 分钟；临时会话不保存。|Uses a small amount of quota. Takes about 1–5 minutes. The temporary chat is not saved.
5 小时剩余额度|5-hour quota remaining
每周剩余额度|Weekly quota remaining
正在自检…|Testing…
正在检查额度并发送一次极小请求，随后复查窗口；约需 1–5 分钟，请勿重复点击。|Checking quota, sending one tiny request, then verifying the window. Takes about 1–5 minutes. Please do not click again.
自检成功：Codex 已实际完成一次极小请求，预热请求链路可用。|Self-test passed: Codex completed a real minimal request. The warm-up request path works.
临时会话连接未能正常关闭，请检查 Codex Loop 后台进程。|The temporary connection did not close normally. Check the Codex Loop background process.
自检未发送请求：额度读取失败、额度不足或当前账号不满足测试条件。|No test request was sent: quota could not be read, quota is exhausted, or this account is not eligible.
请求后的窗口状态尚未确认；不影响上方实际请求完成与否的判定。|The window state after the request could not be confirmed. The request completion result above still applies.
测试使用临时会话，连接已关闭，不保存测试聊天，无需归档。|The test used an ephemeral chat. Its connection is closed; no test chat is saved or needs archiving.
自检未通过：请求可能已发送，但未确认正常完成。不会自动重试，请稍后手动检查。|Self-test inconclusive: a request may have been sent, but completion was not confirmed. It will not be retried automatically.
自检失败：连接、模型选择或请求准备未完成，没有发出模型请求。|Self-test failed before dispatch: connection, model selection, or request preparation did not complete.
计划时间|Scheduled time
连接准备完成|Connection prepared
额度检查开始|Quota check started
请求提交|Request submitted
请求完成|Request completed
窗口确认|Window confirmed
未记录|Not recorded
未知|Unknown
编辑预热时间|Edit warm-up times
只读检查本机 Codex 的连接、额度数据和可用轻量模型，约需 30 秒。不会发送预热请求；检查通过也不保证后续网络请求一定成功。|Read-only check of the local Codex connection, quota and lightweight models. Takes about 30 seconds and sends no warm-up request. A successful check does not guarantee later network requests will succeed.
基于开源项目 UsageLoop 扩展 · 原作者 benthompsondev · MIT License|Based on UsageLoop by benthompsondev · MIT License
感谢开源项目的支持|Thanks to the upstream open-source project
★ 支持原项目 UsageLoop|★ Support the original UsageLoop project
Codex 状态发生变化，未采用旧结果；请重新自检。|Codex changed during the test. The stale result was discarded. Run the self-test again.
本地状态保存失败，请检查存储位置。|Could not save local state. Check the storage location.
自检异常：未能确认请求结果；不会自动重试。|Self-test error: the request outcome is unknown. It will not be retried automatically.
保存失败，时间表未更改。|Save failed. The schedule was not changed.
未检测到本机 Codex，无法验证。|Local Codex was not found. The test cannot run.
每天最多设置 24 个时间点|You can set up to 24 times per day.
时间格式无效|Invalid time format.
时间必须在 00:00 至 23:59 之间|Time must be between 00:00 and 23:59.
请至少添加一个预热时间|Add at least one warm-up time.
当前是 Codex Loop 本地扩展版，尚未配置本项目的更新仓库。请手动更新，避免覆盖为原项目版本。|This local Codex Loop build has no release repository configured. Update it manually to avoid replacing it with the upstream version.
已接收预热检查|Warm-up check accepted
已提交预热检查|Warm-up check submitted
等待执行|Waiting to run
'''
EXTRA_EN = dict(line.split('|',1) for line in PAIRS.splitlines() if '|' in line)
EN_FRAGMENTS = {
'保存失败：':'Save failed: ', '删除预热时间 ':'Remove warm-up time ', '预热时间 ':'Warm-up time ',
'下次定时检查：':'Next scheduled check: ', '　上次计划：':'   Last slot: ', '最近自检 ':'Last self-test ',
'使用模型：':'Model: ', '当前仍是同一轮窗口，重置时间 ':'The same window is still active; resets at ',
'；本次测试没有新开一轮。':'. This test did not start a new window.',
'当前已确认固定重置时间 ':'Confirmed fixed reset time: ',
'；不能单凭本次请求确定新窗口的归因。':'. This request alone does not prove what started the new window.',
'请求前未形成固定倒计时，请求后已确认五小时窗口，重置时间 ':'No fixed countdown existed before the request. A five-hour window was confirmed after it, resetting at ',
'当前固定重置时间 ':'Current fixed reset time: ', '；请求是否成功以以上完成结果为准。':'. See the completion result above for request success.',
'每周额度  剩余 ':'Weekly quota  Remaining ', '5 小时窗口  剩余 ':'5-hour window  Remaining ',
'剩余 ':'Remaining ', '%（已用 ':'% (used ', '%）':'%)', '% · 已用 ':'% · Used ', '% · 重置于 ':'% · Resets ',
'每天 ':'Every day ', ' 检查预热；窗口仍有效时跳过。':' — check warm-up; wait if the current window is still active.',
'今天':'Today', '明天':'Tomorrow', '预热时间':'Warm-up times', '：':': ',
}
