# Codex Loop v1.0.0 发布准备

## 已完成

- 独立的 Codex Loop 安装标识，不复用 UsageLoop 卸载记录；安装脚本不再删除原软件目录。
- 新用户不会从 UsageLoop 目录继承自动预热开关或历史计划；默认自动预热、开机启动关闭。
- 构建包含图标、Python/Qt 动态库、项目 MIT LICENSE 与第三方许可证；源码 wheel 包含图标。
- README 改为当前功能和本仓库下载说明；清除上游赞助按钮与自动化构建入口中的误导链接。
- 公开包只从构建产物与源码白名单生成，不含作者本机的 data、登录凭据、日志、构建工具或设置草稿。

## 你需要准备

1. 你的 GitHub 用户名、仓库名（例如 CodexLoop）、项目介绍；创建仓库时不要用同名空 README 覆盖已有内容。
2. 如需给新增代码添加个人版权，确定真实署名／维护者昵称；原作者 MIT 声明保留，不应替换为只有自己的名字。
3. 将源码压缩包解压后的内容推送到仓库根目录。保留 LICENSE、NOTICE.md、THIRD_PARTY_NOTICES.md、licenses 和图标资源。
4. 在 Releases 创建标签 v1.0.0。首次建议勾选 Pre-release，直到另一台干净 Windows 11 x64 电脑验证通过。
5. 上传 Windows 解压即用包、源码包、依赖源码包与 SHA256SUMS.txt。Qt/PySide/Shiboken 的对应源码需与二进制保持可获取，勿仅提供本项目 MIT 源码代替。
6. 编写发布说明：首次公开版本、功能列表、运行要求、默认开关、已知限制。附两张干净的中文／英文界面截图，隐藏自己的额度或其他个人信息。
7. 在另一台电脑／全新 Windows 用户账户上检查：解压运行、无 Codex 时提示、安装登录 Codex 后兼容性、语言与主题切换、真实预热自检、定时任务、托盘运行、重启恢复和退出。
8. 若要自动更新，再把 src/sentinel/product.py 的发布仓库换成自己的，并重新验证更新器；本次不自动链接或发布你的 GitHub。
9. 已提供 CodexLoop-Setup.exe 安装包，安装路径可自选，安装完成自动创建桌面快捷方式；安装程序尚未进行代码签名。也保留解压即用 ZIP。

## 版本与支持范围

当前公开候选版本为 1.0.0。第一次公开后，代码发生实质变化应增加版本号，不应反复覆盖同一标签的不同二进制文件。不要把对 Windows 11 x64 的验证写成支持所有操作系统、所有电脑或所有 Codex 版本。

## 依赖许可与源码

项目 MIT 许可证不覆盖 Python、Qt 等运行库。源码包与二进制包附带相应许可说明，依赖源码包提供未修改 QtBase、QtSvg 和 PySide/Shiboken 对应源码。兼容的 Qt 动态库可放在 _internal 中替换，本项目不限制为调试其修改而进行的逆向工程。具体依赖条款见 THIRD_PARTY_NOTICES.md 和 licenses/。

依赖来源：https://doc.qt.io/qtforpython-6/licenses.html 、https://www.qt.io/development/open-source-lgpl-obligations 。对外维护仓库时保持源码下载可用；未来更换运行库版本时同步更新许可证、依赖版本清单及对应源码。
