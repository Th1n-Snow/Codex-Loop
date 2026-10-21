"""Local Simplified Chinese UI layer; scheduling and stored state stay upstream-compatible."""
import functools
import re

PAIRS = r'''Dashboard	仪表盘
Settings	设置
About	关于
Automation	自动预热
Schedule	预热计划
Continuous	连续衔接
Once each day	每天一次
Weekly routine	每周计划
Weekdays	工作日
Weekends	周末
Monday	星期一
Tuesday	星期二
Wednesday	星期三
Thursday	星期四
Friday	星期五
Saturday	星期六
Sunday	星期日
Monday through Friday	星期一至星期五
Saturday and Sunday	星期六、星期日
Local-first	本地运行
  for Codex	  Codex 额度预热
Keep your Codex reset clock running.	让 Codex 额度窗口提前开始计时。
Your Codex reset clock	Codex 额度窗口
If Codex reports a 5-hour window, using it starts the next reset clock. With this PC awake, Codex Loop can start the next one while you’re away, so it is already counting down when you return.	如果账号有 5 小时额度窗口，首次请求会启动计时。电脑保持唤醒时，Codex Loop 可以在你开始工作前预热，让下一次重置更早到来。
Codex Loop does not add quota or bypass limits. It uses one minimal request to start your normal next window.	Codex Loop 通过一次极小请求启动正常的额度窗口，不增加额度，也不绕过限制。
Current 5-hour window	当前 5 小时窗口
Weekly allowance	每周额度
Keep my 5-hour windows ready	自动预热 5 小时窗口
Turn Codex Loop automation on or off	开启或关闭自动预热
When should the next 5-hour window start?	何时启动下一个 5 小时窗口？
Start Codex Loop with Windows	登录 Windows 时启动 Codex Loop
Windows startup	开机启动
Opens quietly in the tray, not on screen	登录后在系统托盘静默运行
Start in the tray when you sign in to Windows. Applies to your account only, needs no administrator rights, and is off until you turn it on.	登录 Windows 后在托盘运行，仅对当前用户生效，无需管理员权限。默认关闭。
Choose how Codex Loop keeps your reset clock running.	设置额度窗口的预热方式和时间。
Codex Loop sends no window-start request while this is off.	关闭后不会发送启动额度窗口的请求。
Sends one tiny request to Codex, only when a new window needs to start.	仅在需要启动新窗口时，向 Codex 发送一次极小请求。
Choose continuous rollover, one daily start time, or a weekly routine.	选择连续衔接、每天一次，或每周计划。
Start time	首次预热时间
Local time on this PC. Keep it awake; after restart Codex Loop checks the current schedule.	使用本机时间。电脑需保持唤醒；重启后会重新检查计划。
Once each day start time	每天首次预热时间
Choose when you want your first window to start each day. Codex Loop keeps windows rolling during the day, then pauses overnight so tomorrow's start stays on schedule.	设置每天首次预热的时间。白天自动衔接窗口，夜间暂停，让第二天仍能按计划开始。
Weekdays start time	工作日首次预热时间
Weekends start time	周末首次预热时间
Apply Mon–Fri	应用到周一至周五
Apply Sat–Sun	应用到周六、周日
Apply this time to Monday through Friday.	将此时间应用到星期一至星期五。
Apply this time to Saturday and Sunday.	将此时间应用到星期六、星期日。
Applied	已应用
Customize individual days	分别设置每天的时间
Next routine	下一轮计划
First start	首次预热
Next reset	下次重置
Overnight pause	夜间暂停
Times are approximate and shown in your local time.	时间为近似值，按本机时区显示。
Use a first-start time for each day, then keep windows rolling until it is time to pause for tomorrow.	每天按设定时间首次预热，随后自动衔接，直到进入夜间暂停。
Start the next window after the current reset and safety check.	当前窗口重置并通过检查后，启动下一个窗口。
Wait for the selected local time after the current window ends.	当前窗口结束后，等待设定的本地时间。
Keeps windows rolling during the day, then pauses so tomorrow's first start stays on schedule.	白天自动衔接窗口，夜间暂停，保持第二天的首次预热时间。
As soon as reset passes	重置后立即衔接
Starts the next window after the current reset and safety buffer.	当前窗口重置并经过缓冲时间后，启动下一窗口。
Sync usage	同步额度
Sync complete	同步完成
Syncing…	正在同步…
Checking Codex…	正在检查 Codex…
Recheck Codex compatibility	重新检查 Codex 兼容性
Codex connection	Codex 连接
After updating or signing back in to Codex, recheck here. This reads usage and supported models without sending a model request.	更新 Codex 或重新登录后，可在此检查。只读取额度和可用模型，不发送模型请求。
Checking usage and models. Allow about 30 seconds. No model request is sent.	正在读取额度和模型，约需 30 秒，不发送模型请求。
Compatibility confirmed. Your saved schedule and safety checks still apply.	兼容性检查通过，将按已保存的计划和检查规则运行。
Codex usage was updated from a fixed reset clock.	已根据确认的重置时间更新额度。
Technical details	技术详情
Copy this summary	复制诊断摘要
Safe to paste into a bug report. No prompts, responses, credentials, or account identity are ever recorded.	可用于提交问题反馈，不记录提示词、回复、凭据或账号身份。
Updates	更新
Check for updates	检查更新
No update check has run.	尚未检查更新。
Codex quota warm-up	Codex 额度预热
Support Codex Loop	支持 Codex Loop
★ Support Codex Loop	★ 支持 Codex Loop
GitHub is checked only when you press the button. Update traffic is separate from Codex and cannot use subscription quota.	仅点击按钮时查询 GitHub。更新检查不会消耗 Codex 订阅额度。注意：上游更新可能覆盖本地汉化。
Checking GitHub…	正在查询 GitHub…
Check again	重新检查
Not now	暂不更新
Try again	重试
Download installer	下载安装包
Download update	下载更新
Install update	安装更新
Install and restart	安装并重启
Copy command	复制命令
Safe and private	保护隐私
Codex keeps its own sign-in. Codex Loop never reads credentials.	登录由 Codex 管理，Codex Loop 不读取凭据。
Local and lightweight	本地轻量运行
Countdowns move on this PC with no Codex polling.	倒计时在本机计算，无需轮询 Codex。
Quota protected	额度保护
Weekly allowance is checked, and unclear requests are never retried.	预热前检查每周额度；结果不明确的请求不会自动重试。
Every check runs on this PC. Codex keeps its own sign-in.	所有检查均在本机执行，登录由 Codex 管理。
Private by design  ·  Local-first  ·  No telemetry  ·  No cloud upload	隐私保护  ·  本地运行  ·  无遥测  ·  无云端上传
Start my first window now	立即启动首次窗口
Manage schedule	管理预热计划
Recent starts	最近预热记录
Resume automation	恢复自动预热
Pause until tomorrow	暂停到明天
Pause until tomorrow's first start	暂停到明天首次预热
Return to your saved schedule.	恢复已保存的计划。
Wait for the current operation to finish.	请等待当前操作完成。
Automation stays on.\nYour routine is unchanged.	自动预热仍已开启。\n已保存的计划保持不变。
NEXT ACTION	下一步
CLOCK RUNNING	正在计时
ON	已开启
OFF	已关闭
SAFE	正常
PROTECTED	已保护
NOT CHECKED	尚未检查
Not checked	尚未检查
Not checked yet	尚未检查
Not available	暂无数据
AUTOMATION OFF	自动预热已关闭
PAUSED · ON	已暂停 · 开关已开启
PAUSED	已暂停
CHECKING CONNECTION	正在检查连接
Checking Codex compatibility	正在检查 Codex 兼容性
Reading usage and supported models. No model request is sent.	正在读取额度和可用模型，不发送模型请求。
Codex confirmed this reset time. No Codex traffic is needed for the countdown.	重置时间已由 Codex 确认，倒计时不会产生网络请求。
Codex confirms this reset time. The countdown runs locally with no Codex traffic.	重置时间已由 Codex 确认，倒计时在本机计算。
No automatic requests while automation is off	自动预热关闭期间不会自动发送请求
Not available in the last read-only sync	上次只读同步未取得此数据
Last automatic start: None yet	上次自动预热：暂无
Last automatic start: History unavailable	上次自动预热：记录暂不可用
Last automatic start: Successful	上次自动预热：成功
Last automatic start: Outcome unclear · No retry	上次自动预热：结果不明确，不会重试
Last automatic start: Stopped before sending	上次自动预热：发送前已停止
Automatic start in progress	正在自动预热
NEEDS ATTENTION	需要处理
Needs attention	需要处理
Ready	已就绪
Waiting	等待中
Checking	检查中
Detected	已检测到
STARTING NEXT WINDOW	正在启动下一窗口
Starting the next reset clock	正在启动下一轮计时
One minimal Codex request is in progress. It will not be retried automatically.	正在发送一次极小请求，不会自动重试。
WAITING FOR RESET	等待重置
Reset time not verified	重置时间尚未确认
Reset time unavailable	暂无重置时间
No clock running yet	尚未开始计时
No reset clock verified yet	尚未确认重置时间
Set up your routine	设置预热计划
Choose when your day starts in Settings, then turn on Automation. Nothing is sent to Codex until you do.	请在设置中选择每日首次预热时间，再开启自动预热。开启前不会向 Codex 发送请求。
Choose a start time, then turn on Automation.	选择首次预热时间后，开启自动预热。
Choose your start time in Settings, then turn on Automation	在设置中选择首次预热时间，然后开启自动预热
Checking the Codex connection	正在检查 Codex 连接
Codex Loop must confirm this Codex version before a start.	预热前需要确认当前 Codex 版本的兼容性。
Compatibility not checked	尚未检查兼容性
A read-only compatibility check is needed.	需要进行一次只读兼容性检查。
Start blocked until Codex passes a compatibility check.	兼容性检查通过后才能预热。
Start blocked while Codex reconnects. Next check 	正在重新连接 Codex，暂不预热。下次检查：
Automation is off	自动预热已关闭
No automatic starts. Your saved routine remains available.	不会自动预热，已保存的计划仍保留。
No automatic Codex request will be sent.	不会自动向 Codex 发送请求。
WAITING	等待中
CHECKING	检查中
RECONNECTING	正在重新连接
OVERNIGHT PAUSE	夜间暂停
GET STARTED	开始设置
NO RETRY	不会重试
START NOT CONFIRMED	启动尚未确认
Automatic starts are paused. Recheck Codex when ready.	自动预热已暂停，可重新检查 Codex 后继续。
Start not confirmed	预热尚未确认
Start outcome is unconfirmed	预热结果尚未确认
A request may have been sent. Codex Loop will not retry that attempt.	请求可能已发送，Codex Loop 不会重复尝试。
No retry for the uncertain start. Check Recent starts.	结果不明确，不会重试。请查看最近预热记录。
Your routine is waiting for its next first start.	正在等待下一次首次预热时间。
Waiting for first start	等待首次预热
The previous window ended. Your saved routine is paused overnight.	上一个窗口已结束，计划已进入夜间暂停。
Waiting for your scheduled start	等待计划预热时间
Waiting for saved start	等待设定时间
Safety checks are due	正在进行预热前检查
Safety checks are due now	现在进行预热前检查
Daytime rollover safety checks are due now	现在检查是否可以衔接日间窗口
Scheduled first start is due now	已到首次预热时间
Current window stays active until it resets	当前窗口保持有效，直到重置
First window starts only when you ask	首次窗口需手动启动
No automatic start needed yet	暂不需要自动预热
Current window was already running	当前窗口已经启动
No request was sent	未发送请求
Not sent	未发送
Confirmed	已确认
Not confirmed	尚未确认
Not verified · No retry	尚未确认，不会重试
Outcome unclear · No retry	结果不明确，不会重试
Stopped before sending	发送前已停止
Did my window start?	额度窗口启动了吗？
Your latest 10 start attempts, newest first. All times are local to this PC.	显示最近 10 次预热尝试，新记录在前。全部使用本机时间。
Only Codex Loop start attempts appear here. Syncs, pauses, and time with the app closed or the PC asleep are not recorded as starts. A confirmed start is not a guarantee of remaining quota.	此处仅记录 Codex Loop 的预热尝试。同步、暂停、软件退出或电脑休眠不算预热。启动成功不代表额度一定仍有剩余。
Refresh history	刷新记录
Reread local history only. Makes no Codex requests.	仅读取本地记录，不向 Codex 发送请求。
Close	关闭
Automatic start	自动预热
Manual first start	手动首次预热
No starts recorded yet. Starts made by Codex Loop will appear here after you use it.	暂无预热记录。Codex Loop 发起预热后，记录会显示在这里。
Preparation was recorded, but no completed start was saved.	已记录准备过程，但尚无完成启动的记录。
Codex confirmed a running five-hour reset clock after this start.	Codex 已确认此次预热后启动了 5 小时计时。
No start request was sent. The normal schedule can check again when it is safe.	没有发送启动请求。后续计划会在条件允许时再次检查。
The start could not be confirmed. Codex Loop will not retry this attempt because a request may have been sent.	无法确认是否启动。请求可能已发送，因此不会重试。
A start was attempted, but its outcome was not saved. Codex Loop will not retry this attempt.	已尝试预热，但未保存结果，不会重试。
A request may have reached Codex. No confirmed reset was saved; this attempt will not be retried.	请求可能已到达 Codex，但未保存确认后的重置时间，不会重试。
A small local-first app that keeps your normal Codex reset clock moving.	在本机运行的 Codex 额度窗口预热工具。
Project links	项目链接
View source	查看源码
Releases	版本发布
Report a problem	反馈问题
Request a feature	功能建议
Finding Codex Loop useful?	觉得 Codex Loop 好用？
★ Open GitHub to star Codex Loop	★ 在 GitHub 上为项目点星
A GitHub star helps other Codex users discover the project and lets us know it’s worth continuing to improve.	在 GitHub 点星可以帮助其他 Codex 用户发现项目，也能支持作者继续改进。
Codex support	Codex 兼容性
Privacy and safety	隐私与安全
Codex keeps its own sign-in. Codex Loop never reads tokens, credentials, conversations, or account identifiers.	登录由 Codex 管理。Codex Loop 不读取令牌、凭据、对话或账号标识。
Codex Loop checks that the installed Codex client still supports every action it needs before automation runs.	自动预热前，会检查当前 Codex 客户端是否支持所需功能。
Codex Loop is an independent open-source project. It is not affiliated with, endorsed by, or sponsored by OpenAI. Codex behavior can evolve, so compatibility is checked by capability instead of trusting a version string.	Codex Loop 是独立开源项目，与 OpenAI 无隶属、背书或赞助关系。Codex 的行为可能变化，因此会实际检查兼容性。
Codex reports a 5-hour window	Codex 提供 5 小时额度窗口
The clock begins when Codex is used.	使用 Codex 后开始计时。
Codex Loop starts the next one	Codex Loop 提前启动下一窗口
One minimal request can begin it while this PC is awake.	电脑唤醒时，通过一次极小请求启动窗口。
No shortcuts or extra quota	遵循账号额度限制
Your existing limits and weekly protection still apply.	现有使用限制和每周额度保护继续生效。
Setting not saved	设置未保存
Startup setting not changed	启动设置未更改
Copy failed	复制失败
Summary not copied	摘要未复制
Keep your Codex reset clock running?	开启自动预热？
Start my first window now?	立即启动首次额度窗口？
Codex Loop first checks quota without spending it. Only if no window is running and the safety checks pass will it send one small request and verify the reset clock. Your chosen routine then takes over. An unclear start is not retried.	先以只读方式检查额度；仅在当前没有运行中的窗口且检查通过时，发送一次极小请求并确认重置时间，之后按计划运行。结果不明确时不会重试。
 will use your signed-in Codex client only after its safety checks pass. It checks weekly allowance, sends one minimal request, then verifies the reset.\n\nStarting a window uses a small amount of your plan. An action whose outcome is unclear is never retried.	仅在检查通过后使用已登录的 Codex：检查每周额度，发送一次极小请求，再确认重置时间。\n\n启动窗口会消耗少量额度。结果不明确时不会自动重试。
Select the hour, minute, or AM/PM. Type a value or use the arrow controls.	选择小时或分钟，可直接输入，也可使用箭头调整。
Local time. Select the hour, minute, or AM/PM, then type or use arrow keys.	使用本机时间。选择小时或分钟后输入，或使用方向键调整。
'''
EXACT = dict(line.split('\t',1) for line in PAIRS.splitlines() if '\t' in line)
EXACT = {k.replace('\\n','\n'):v.replace('\\n','\n') for k,v in EXACT.items()}
EXACT.update({'Everything is set': '已准备就绪', 'The countdown runs locally. Codex Loop follows your saved schedule after this window ends.': '倒计时在本机运行。当前窗口结束后，Codex Loop 会按已保存的计划继续预热。', 'TOMORROW': '明天', 'TODAY': '今天', 'If Codex reports a 5-hour window, a new one begins when you use Codex. If the previous window ends while you’re away, the next reset clock normally waits until you come back and use Codex again. With this PC awake, Codex Loop can start that next window with one minimal request, so its reset clock can already be counting down before you return. Codex Loop does not increase your quota or bypass limits.': '对于提供 5 小时窗口的账号，使用 Codex 才会启动新窗口。旧窗口在你离开期间结束时，下一轮通常会等到你再次使用才开始。只要电脑保持唤醒，Codex Loop 就能通过一次极小请求提前预热，让你回来前已开始计时。它不增加额度，也不绕过限制。', '• Codex automation is off until you switch it on\n• Update checks run only when you press the button, and never touch your plan\n• Countdowns are calculated locally and cause no Codex traffic\n• A request whose outcome is unclear is never retried automatically\n• Weekly limits are respected before any action is considered': '• 自动预热由你手动开启\n• 仅点击按钮时检查更新，不消耗 Codex 额度\n• 倒计时在本机计算，不产生 Codex 网络请求\n• 结果不明确的请求不会自动重试\n• 预热前检查每周额度限制', 'Weekly allowance protected': '每周额度已受保护', 'Codex Loop will not start another window while weekly use is this high.': '每周额度用量过高，暂不启动新窗口。', 'WEEKLY PROTECTED': '每周额度保护中', 'Weekly limit near its end': '每周额度即将耗尽', 'The weekly safety check is blocking starts.': '每周额度检查阻止了本次预热。', 'Automatic starts wait for weekly allowance to recover.': '等待每周额度恢复后再自动预热。', 'No five-hour start to schedule': '当前没有可预热的 5 小时窗口', "Codex isn't reporting a five-hour window right now. There's no five-hour start to schedule.": 'Codex 当前没有返回 5 小时窗口，无需安排此类预热。', 'NO 5-HOUR WINDOW': '无 5 小时窗口', 'No five-hour window': '无 5 小时窗口', 'No five-hour start is available to schedule.': '当前没有可安排的 5 小时窗口预热。', 'Weekly evidence unavailable': '每周额度数据不可用', 'WEEKLY NOT CHECKED': '每周额度尚未检查', 'Codex Loop cannot confirm the weekly safety check, so starts remain blocked.': '无法确认每周额度，暂不预热。', 'Weekly check unavailable': '无法检查每周额度', 'Sync usage to get a valid weekly reading.': '请同步额度以获取有效的每周数据。', 'Start blocked until weekly evidence is available.': '取得每周额度数据后才能预热。', 'Codex usage needs a check': '需要检查 Codex 额度', 'Usage unclear': '额度状态不明确', 'The quota readings are inconsistent or cannot be interpreted safely.': '额度数据不一致或无法可靠判断。', 'Sync usage to read the current state.': '请同步额度以读取当前状态。', 'Start blocked until quota evidence is clear.': '确认额度状态后才能预热。', 'Ready when you choose to start': '可手动启动首次窗口', 'Starting a first window requires your approval.': '首次窗口需由你确认启动。', 'FIRST START': '首次预热', 'The first start uses a guarded Codex request after you approve it.': '你确认后，通过一次经过检查的 Codex 请求启动首次窗口。', 'Schedule needs attention': '预热计划需要处理', 'The saved schedule cannot be read safely.': '无法读取已保存的预热计划。', 'Schedule unavailable': '预热计划不可用', 'Start blocked until the saved schedule is usable.': '计划可用后才能预热。', 'Copy this summary': '复制诊断摘要', 'A safe check needs attention': '检查遇到问题', 'Nothing was retried. Diagnostics has the technical reason.': '未进行重试，具体原因可在技术详情中查看。', 'The previous window ended. Codex Loop will follow your saved time.': '上一窗口已结束，将按已保存的时间预热。', 'Last checked quota remains visible below.': '下方继续显示上次读取的额度。', 'Codex Loop is checking whether the next start is safe.': '正在检查是否可以启动下一窗口。', 'Next window due': '已到下次预热时间', 'A start still needs fresh quota and history checks.': '启动前仍需读取最新额度并检查记录。', 'Waiting for first window': '等待首次窗口', 'Codex Loop stopped safely': 'Codex Loop 已停止预热', 'Reconnecting to Codex': '正在重新连接 Codex', 'Codex Loop is retrying read-only compatibility checks.': '正在重试只读兼容性检查。', 'No model request is sent during recovery.': '恢复连接期间不发送模型请求。', 'Checking Codex again': '正在重新检查 Codex', 'Paused until ': '暂停至 ', 'No request sent': '未发送请求', 'No supported lightweight Codex model': '没有支持的轻量 Codex 模型', 'Codex Loop will check Codex and start the first window only after every safety gate passes.': 'Codex Loop 会检查 Codex，所有条件通过后才启动首次窗口。', 'Codex Loop could not save that setting, so it was changed back. Automatic starts are paused until local state can be written again.': '设置保存失败，已恢复原值。可正常保存本地状态后再恢复自动预热。'})
FRAGMENTS = {
'5-hour window  ':'5 小时窗口  ', 'Weekly allowance  ':'每周额度  ',
'% used · resets ':'% 已用 · 重置于 ', '% used':'% 已用',
'Last synced ':'上次同步：', 'Resets at ':'重置时间：', 'Resets ':'重置于 ',
'resets ':'重置于 ', 'Previous window ended ':'上一窗口结束于 ',
'Last automatic start: ':'上次自动预热：',
'Next start around ':'下次预热约在 ', ', after this window resets':'，当前窗口重置后启动',
'After this window: overnight pause · first start ':'当前窗口结束后夜间暂停 · 首次预热：',
'Next start ':'下次预热：', 'Waiting for scheduled start ':'等待计划预热时间：',
'Overnight pause · first start ':'夜间暂停 · 首次预热：',
'Pause until tomorrow\'s first start: ':'暂停到明天首次预热：',
'Pause until ':'暂停到 ', 'Resumes ':'恢复于 ',
'Start my first window now':'立即启动首次窗口',
'See which window starts were confirmed, not sent, or left uncertain.':'查看已确认、未发送及结果不明确的预热记录。',
'Installed version  ':'当前版本  ', 'You are on the latest version (':'当前已是最新版本（',
'Version ':'版本 ', 'About ':'关于 ', ' · MIT licensed':' · MIT 开源许可',
'Open Codex Loop':'打开 Codex Loop', 'Quit Codex Loop':'退出 Codex Loop',
'Model: ':'模型：', ' · Reasoning: ':' · 推理强度：', 'Last recorded: ':'最后记录：',
'Not recorded':'未记录', ' first start':' 首次预热', ' start time':'首次预热时间',
': first start around ': '：首次预热约 ', ' · next reset around ':' · 下次重置约 ',
'Overnight pause begins around ':'夜间暂停约从 ',
'Monday through Friday':'星期一至星期五', 'Saturday and Sunday':'星期六、星期日',
'Monday':'星期一','Tuesday':'星期二','Wednesday':'星期三','Thursday':'星期四',
'Friday':'星期五','Saturday':'星期六','Sunday':'星期日',
'Today at ':'今天 ', 'Tomorrow at ':'明天 ', 'today at ':'今天 ', 'tomorrow at ':'明天 ',
' each day':'（每天）', 'Not checked':'尚未检查', 'Not available':'暂无数据',
'No reset information':'暂无重置时间', 'Time unavailable':'时间暂不可用',
}


EXACT.update({
    'Checks warm-up at your scheduled times each day': '每天按设定时间执行预热检查',
    'Checks warm-up at your scheduled times': '按设定时间执行预热检查',
    'Follows your saved warm-up times': '按已保存的时间检查预热',
    'Theme color': '主题色',
    'Classic mint': '经典薄荷',
    'Peach blossom': '桃夭',
    'Checks your quota window at the scheduled times and warms up when needed.': '到点后检查额度窗口，必要时发起预热。',
})

def _translate_zh(text):
    if not isinstance(text,str):
        return text
    if text in EXACT:
        return EXACT[text]
    if text.startswith(('▸  ', '▾  ')):
        return text[:3]+translate(text[3:])
    result=text
    for a,b in sorted(FRAGMENTS.items(),key=lambda p:len(p[0]),reverse=True):
        result=result.replace(a,b)
    result=re.sub(r'(?<![A-Za-z])(\d+)h (\d+)m',lambda m:f'{m[1]} 小时 {m[2]} 分钟',result)
    result=re.sub(r'(?<![A-Za-z])(\d+)m (\d+)s',lambda m:f'{m[1]} 分 {m[2]} 秒',result)
    result=result.replace(' left',' 后重置')
    # Windows strftime is locale-dependent; normalize English clock output too.
    result=re.sub(r'\b(\d{1,2}):(\d{2}) (AM|PM)\b', lambda m:f'{int(m[1])%12+(12 if m[3]=="PM" else 0):02d}:{m[2]}', result)
    result=re.sub(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b',lambda m:{'Mon':'周一','Tue':'周二','Wed':'周三','Thu':'周四','Fri':'周五','Sat':'周六','Sun':'周日'}[m[0]],result)
    return result


from .i18n_extra import EXTRA_EN, EN_FRAGMENTS
import weakref
from contextlib import contextmanager

EXACT.update({en: zh for zh, en in EXTRA_EN.items()})
EXACT[
    'Codex Loop will use your signed-in Codex client only after its safety checks '
    'pass. It checks weekly allowance, sends one minimal request, then verifies the reset.\n\n'
    'Starting a window uses a small amount of your plan. An action '
    'whose outcome is unclear is never retried.'
] = (
    'Codex Loop 仅在安全检查通过后，才会使用你已登录的 Codex 客户端。'
    '软件会检查每周剩余额度，发送一次极小请求，然后确认窗口重置时间。\n\n'
    '启动额度窗口会消耗少量套餐额度。结果不明确的请求不会自动重试。'
)
FRAGMENTS["Recent starts"] = "最近预热记录"
FRAGMENTS["Usage refreshes automatically: about every minute on the dashboard and every five minutes in the background. Warm-ups take priority. Click to sync now."] = "额度会自动同步：仪表盘约每分钟一次，后台约每五分钟一次；预热任务优先。点击可立即同步。"
_language = "zh_CN"
_installed = False
_retranslating = False
_tracked = weakref.WeakSet()


def current_language():
    return _language


def translate(text):
    if not isinstance(text, str):
        return text
    if _language == "zh_CN":
        return _translate_zh(text)
    if text in EXTRA_EN:
        return EXTRA_EN[text]
    if not re.search(r'[\u4e00-\u9fff]', text):
        return text
    reverse = {value: key for key, value in EXACT.items()}
    if text in reverse:
        return reverse[text]
    result = text
    fragments = {value: key for key, value in FRAGMENTS.items()}
    fragments.update(EN_FRAGMENTS)
    for source, target in sorted(fragments.items(), key=lambda pair: len(pair[0]), reverse=True):
        result = result.replace(source, target)
    result = re.sub(r'(\d+) 小时 (\d+) 分钟', r'\1h \2m', result)
    result = re.sub(r'(\d+) 分 (\d+) 秒', r'\1m \2s', result)
    return result


def _remember(obj, key, raw):
    if _retranslating:
        return
    if not hasattr(obj, '_loop_i18n_sources'):
        obj._loop_i18n_sources = {}
    obj._loop_i18n_sources[key] = raw
    _tracked.add(obj)


def _wrap(cls, name, constructor=False):
    old = getattr(cls, name)
    @functools.wraps(old)
    def wrapped(self, *args, **kwargs):
        raw = next((value for value in args if isinstance(value, str)), kwargs.get('text'))
        # QComboBox userData is an internal value, never translated.
        if name in {'addItem', 'setItemText'}:
            values = list(args)
            index = next((i for i, value in enumerate(values) if isinstance(value, str)), None)
            if index is not None:
                values[index] = translate(values[index])
            mapped = tuple(values)
        else:
            mapped = tuple(translate(value) if isinstance(value, str) else value for value in args)
        kw = {key: translate(value) if isinstance(value, str) and key in {'text','title','toolTip','accessibleName'} else value for key,value in kwargs.items()}
        result = old(self, *mapped, **kw)
        if isinstance(raw, str):
            if constructor:
                _remember(self, 'setText', raw)
            elif name == 'addItem':
                _remember(self, ('item', self.count()-1), raw)
            elif name == 'setItemText':
                _remember(self, ('item', args[0]), raw)
            elif name == 'addAction' and result is not None:
                _remember(result, 'setText', raw)
            elif name != 'showMessage':
                _remember(self, name, raw)
        return result
    setattr(cls, name, wrapped)


def install():
    global _installed
    if _installed:
        return
    _installed = True
    from PySide6.QtCore import QLocale
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QLabel,QPushButton,QCheckBox,QRadioButton,QWidget,QMenu,QMessageBox,QComboBox,QSystemTrayIcon,QTimeEdit
    QLocale.setDefault(QLocale('zh_CN'))
    for cls in (QLabel,QPushButton,QCheckBox,QRadioButton,QAction,QMenu):
        _wrap(cls,'__init__',True)
    for cls in (QLabel,QPushButton,QCheckBox,QRadioButton,QAction):
        _wrap(cls,'setText')
    for method in ('setToolTip','setWindowTitle','setAccessibleName','setAccessibleDescription'):
        _wrap(QWidget,method)
    for method in ('addItem','setItemText'):
        _wrap(QComboBox,method)
    _wrap(QMenu,'addAction')
    for method in ('setToolTip','showMessage'):
        _wrap(QSystemTrayIcon,method)
    for method in ('question','warning','information','critical'):
        old=getattr(QMessageBox,method)
        def static(*args,_old=old,**kwargs):
            return _old(*(translate(value) for value in args),**kwargs)
        setattr(QMessageBox,method,staticmethod(static))
    old_format=QTimeEdit.setDisplayFormat
    QTimeEdit.setDisplayFormat=lambda self,fmt:old_format(self,'HH:mm')
    from .ui_components import ElidingLabel
    _wrap(ElidingLabel,'__init__',True)
    _wrap(ElidingLabel,'setText')


def set_language(language, app=None):
    global _language, _retranslating
    from PySide6.QtCore import QLocale
    from shiboken6 import isValid
    _language = language if language in {'zh_CN', 'en'} else 'zh_CN'
    QLocale.setDefault(QLocale('zh_CN' if _language == 'zh_CN' else 'en_US'))
    if app is not None:
        apply_app_locale(app)
    _retranslating = True
    try:
        for obj in list(_tracked):
            if not isValid(obj):
                continue
            blocked = obj.blockSignals(True)
            try:
                for key, raw in list(obj._loop_i18n_sources.items()):
                    if isinstance(key, tuple):
                        if key[1] < obj.count():
                            obj.setItemText(key[1], raw)
                    else:
                        method = getattr(obj, key, None)
                        if method is not None:
                            method(raw)
            finally:
                obj.blockSignals(blocked)
    finally:
        _retranslating = False


def apply_app_locale(app):
    from PySide6.QtGui import QFont
    from PySide6.QtCore import QTranslator, QLibraryInfo
    app.setFont(QFont('Microsoft YaHei UI' if _language == 'zh_CN' else 'Segoe UI',10))
    previous = getattr(app, '_usage_loop_zh_translator', None)
    if previous is not None:
        app.removeTranslator(previous)
        app._usage_loop_zh_translator = None
    if _language == 'zh_CN':
        translator = QTranslator(app)
        if translator.load('qtbase_zh_CN', QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(translator)
            app._usage_loop_zh_translator = translator
