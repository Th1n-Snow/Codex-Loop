# Codex Loop

本地运行的 Codex 额度窗口预热与查看工具。当前发布目标：**Windows 11 x64**，界面支持简体中文与 English。

## v1.1.3 中文界面修复

补齐兼容性检查及异常详情等中文提示，检查仪表盘、同步、自检、记录、弹窗、更新和托盘的全部已知显示分支；新增防漏翻译检查，428 项发布检查通过。[检查范围](docs/LOCALIZATION_COVERAGE.md)。

## v1.1.2 界面调整

移除 Windows 主窗口标题栏最左上角的小图标，保留页面环形标记、任务栏与托盘图标。

## v1.1.1 修复

补齐异常状态的中文提示；桃夭主题左侧警告条使用主题粉色，“需要处理”标签和安全保护继续生效。

## v1.1.0 外观与交互更新

- 新增“桃夭”主题色：浅色使用淡粉与玫红，深色使用炭灰与柔粉；可与经典薄荷、跟随系统／浅色／深色自由组合，设置即时保存。
- 仪表盘重新排布：更紧凑的状态栏、并排同步／自检按钮、带百分比的剩余额度条、横向每周额度；小窗口自动上下排列。
- 保留窗口卡片左侧状态色条，增加操作图标，完善未保存修改、保存成功和悬停提示。
- 自动预热卡片精简，时间仍在上方编辑；托盘仍可临时暂停。原有时间表和记录在升级后保留。

## v1.0.1 调度规则（继续适用）

已删除按五小时重置边界连续自动预热的后台入口。自动预热只由保存的每日时间点触发；窗口到期本身不再发起请求。旧 continuous 配置升级后会先关闭自动预热，请确认时间表后再开启。定时任务到点后等待旧窗口结束的单次队列仍保留。

## 功能

- 每天设置多个预热时间，提前准备只读连接；旧窗口仍有效时排队等待。
- 仪表盘查看五小时与每周剩余额度，前台约一分钟、后台约五分钟自动检查刷新；读取确认另有连接耗时。
- 真实请求链路自检，使用不保存聊天的临时会话；记录预热各阶段时间。
- 经典薄荷／桃夭主题色，跟随系统／浅色／深色配色，语言即时切换。
- 托盘运行、可选开机启动；时间编辑恢复原值后清除未保存提示。

## 下载与运行

推荐在 [本仓库 Releases](https://github.com/Th1n-Snow/Codex-Loop/releases) 下载 `CodexLoop-Setup.exe`，双击后选择安装语言、接受许可证、选择安装目录，安装完成会自动创建桌面和开始菜单快捷方式。无需管理员权限，受保护目录可能不可写，请选择自己的 D/E 盘 Apps 文件夹。

也可以获取 `CodexLoop-1.1.3-windows-x64.zip`，解压整个文件夹后运行 `CodexLoop.exe`。可解压到 D 盘或 E 盘。

**不能只复制 exe**，必须保留旁边的 `_internal`、许可证与其他文件。运行发布包无需另装 Python。

1. 在自己的电脑安装并登录 Codex 桌面客户端，或安装能在 PATH 中找到的 Codex CLI。
2. 打开 Codex Loop，进入设置，检查 Codex 兼容性。
3. 如需验证真实请求链路，可点击仪表盘的“预热自检”；会消耗少量正常额度。
4. 设置自己的每日时间，保存并启用自动预热。
5. 关闭窗口后通常在托盘继续运行；从托盘退出后不再执行。电脑需保持开机、唤醒和联网。

默认简体中文、跟随系统配色，自动预热和开机启动默认关闭。个人配置与记录保存在 `%LOCALAPPDATA%\CodexLoop`，不随发布包携带。解压即用不等于数据随文件夹移动。

首次运行时 Windows 可能提示该程序未经签名；请核对下载来源和发布的 SHA-256。不要为了运行软件关闭系统防护。

## 功能边界

软件通过本机 Codex app-server 读取额度，预热时发送一次极小的正常请求。它不增加额度、不重置有效窗口、不绕过限制，也不保证网络请求一定成功。订阅必须支持对应的五小时窗口。额度显示是定期读取，不是服务端逐秒推送。

兼容性检查通过只说明连接、额度结构和轻量模型满足要求；完整请求链路需通过自检或一次真实预热验证。Codex 更新后可能需要重新检查兼容性。

项目链接已接入 https://github.com/Th1n-Snow/Codex-Loop ，更新按钮只查询本项目正式 Release；更新安装包需通过 SHA-256 校验。升级时请在安装向导选择原安装目录；个人设置与记录保留。当前验证不涵盖 macOS、Windows ARM、Windows 10 或所有 Codex 客户端版本。

## 从源码运行与构建

使用 Python 3.11 或更高版本，在项目目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -c requirements-build.txt -e ".[build,test]"
.\.venv\Scripts\python -m sentinel.app
.\.venv\Scripts\python scripts/verify-release.py
.\.venv\Scripts\python scripts/render_icon.py
.\.venv\Scripts\python scripts/render_version_info.py
.\.venv\Scripts\python -m PyInstaller --noconfirm packaging/CodexLoop.spec
```

构建输出位于 `dist/CodexLoop`。完整发布说明见 [发布准备](docs/RELEASE_PREPARATION.md)；已验证范围和旧测试限制见 [发布验证](docs/RELEASE_VERIFICATION.md)。

## 来源与许可证

本项目基于 [UsageLoop](https://github.com/benthompsondev/usageloop) 扩展，原作者 Ben Thompson（benthompsondev）。保留原有版权声明，项目代码采用 [MIT](LICENSE) 许可证。原项目历史文档单独保存在 [上游文档](docs/UPSTREAM_README.md)，其中下载地址与原有功能不代表当前发行版。

打包程序另含 Python、Qt/PySide6/Shiboken 等第三方组件，适用各自许可证，见 [第三方说明](THIRD_PARTY_NOTICES.md) 和 `licenses/`。本项目独立维护，与 OpenAI、UsageLoop 原作者及 Qt 公司无隶属或背书关系。

## English

Codex Loop schedules small, ordinary Codex requests to prepare a usage window ahead of work. It provides daily time slots, read-only quota refresh, ephemeral request self-tests, and light/dark themes with Chinese/English UI.

Extract the complete Windows x64 release folder and run `CodexLoop.exe`; Python is not required. Install and sign in to Codex separately. Automation and start-at-login are disabled by default. Keep the computer awake and connected. This does not increase quota or bypass restrictions. Personal state is stored under `%LOCALAPPDATA%\CodexLoop`. The code is MIT licensed; bundled dependencies retain their own licenses.
