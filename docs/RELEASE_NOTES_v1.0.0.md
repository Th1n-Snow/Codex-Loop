# Codex Loop v1.0.0 — 首次公开候选版本

- 每天多个时间预热、提前准备连接、旧窗口有效时等待后衔接。
- 五小时与每周剩余额度展示，前台／后台自动只读刷新。
- 真实请求链路自检，临时聊天不保存；预热阶段记录。
- 简体中文与 English、浅色／深色／跟随系统配色。
- 改善时间输入滚轮和圆角边框、未保存提示与 Windows 标题栏。

## 使用要求

Windows 11 x64；自行安装并登录 Codex；账号提供对应额度窗口；电脑保持唤醒、联网，Codex Loop 保持运行。解压整个 ZIP 后运行 exe，无需另装 Python。软件未签名。

本项目不增加额度、不绕过限制，预热和自检会消耗少量正常额度。Codex 兼容性、登录与网络受每台电脑环境影响。首次建议作为 Pre-release，并在另一台电脑完成验证后转正式版本。

## 文件

- CodexLoop-Setup.exe：可选安装路径，自动创建桌面和开始菜单快捷方式，支持简体中文／English 安装向导。
- CodexLoop-1.0.0-windows-x64.zip：解压即用运行包。
- CodexLoop-1.0.0-source.zip：上传到 GitHub 仓库的项目源码。
- CodexLoop-1.0.0-dependency-sources.zip：QtBase、QtSvg、PySide/Shiboken 对应未修改源码，随运行包保持可获取。
- SHA256SUMS.txt：下载完整性校验。

来源与许可证见仓库 README、LICENSE、NOTICE 和第三方说明。项目跳转与更新查询已接入 Th1n-Snow/Codex-Loop。
