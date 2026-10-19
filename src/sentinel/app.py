"""Codex Loop desktop entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QWidget

from .app_controller import ApplicationController
from .app_state import AppStateStore, app_data_root
from .desktop import DesktopShell, MainWindow
from .history import SafeHistory
from .product import PRODUCT
from .providers import CodexProvider
from .single_instance import ActivationChannel, InstanceCoordinator, SingleInstanceGuard
from .startup import create_startup_manager, reconcile_startup_preference


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=Path(PRODUCT.executable_name).stem)
    parser.add_argument(
        "--background",
        action="store_true",
        help="Start in the system tray without opening the main window.",
    )
    parser.add_argument("--activation-smoke", help=argparse.SUPPRESS)
    parser.add_argument(
        "--activation-smoke-auto-hide", action="store_true", help=argparse.SUPPRESS
    )
    return parser


def _run_activation_smoke(
    application: QApplication, name: str, *, background: bool, auto_hide: bool
) -> int:
    """Packaged Windows acceptance path. It never constructs a provider."""
    guard = SingleInstanceGuard(f"Local\\Codex Loop-activation-smoke-{name}")
    channel = ActivationChannel(f"Codex Loop-activation-smoke-{name}")
    if not InstanceCoordinator(guard, channel).claim(background=background):
        return 0
    window = QWidget()
    window.setWindowTitle("Codex Loop activation smoke")
    window.resize(420, 180)

    def restore() -> None:
        window.showNormal()
        window.raise_()
        window.activateWindow()

    channel.activation_requested.connect(restore)
    application._sentinel_window = window  # type: ignore[attr-defined]
    application._sentinel_instance_guard = guard  # type: ignore[attr-defined]
    application._sentinel_activation_channel = channel  # type: ignore[attr-defined]
    if not background:
        window.show()
        if auto_hide:
            QTimer.singleShot(500, window.hide)
    return application.exec()


def restore_upgrade_draft(window, settings, path: Path) -> None:
    """Restore an updater's unsaved editor handoff without activating it."""
    import json
    from .schedule import normalize_multi_times
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if (not isinstance(payload, dict) or payload.get("consumed") is True
                or payload.get("saved_times") != [list(value) for value in settings.multi_start_times]):
            return
        values = normalize_multi_times(payload.get("values"))
        if not values:
            return
        window.multi_time_panel.set_times(values,reset_baseline=False)
        if values != settings.multi_start_times:
            window.multi_time_panel.mark_dirty()
        result = payload.get("self_test_result")
        card = window.provider_cards.get("codex")
        if isinstance(result, str) and result.startswith("最近自检 ") and card is not None:
            card.verification_label.setText(result)
            from .ui_theme import feedback_style
            feedback_style(card.verification_label, "success" if "自检成功：" in result else "warning")
            card.fit_wrapped_text()
        payload["consumed"] = True
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError, TypeError):
        return


def main(argv: list[str] | None = None) -> int:
    from .zh_cn import install, apply_app_locale
    install()
    args = create_parser().parse_args(argv)
    application = QApplication.instance() or QApplication(sys.argv[:1])
    apply_app_locale(application)
    if args.activation_smoke:
        return _run_activation_smoke(
            application,
            args.activation_smoke,
            background=args.background,
            auto_hide=args.activation_smoke_auto_hide,
        )
    instance_guard = SingleInstanceGuard(PRODUCT.single_instance_name)
    activation_channel = ActivationChannel(PRODUCT.single_instance_name)
    coordinator = InstanceCoordinator(instance_guard, activation_channel)
    if not coordinator.claim(background=args.background):
        return 0
    application.setApplicationName(PRODUCT.display_name)
    application.setApplicationVersion(PRODUCT.version)
    application.setOrganizationName(PRODUCT.publisher)
    application.setStyle("Fusion")

    history = SafeHistory()
    providers = [CodexProvider(history=history)]
    controller = ApplicationController(
        providers, AppStateStore(), error_history=history
    )
    controller.start()
    startup = create_startup_manager(str(Path(sys.executable).resolve()))
    try:
        normalized_startup = reconcile_startup_preference(
            controller.settings.start_with_windows, startup
        )
        if normalized_startup != controller.settings.start_with_windows:
            durable_startup = controller.settings.start_with_windows
            if not controller.set_start_with_windows(normalized_startup):
                startup.set_enabled(durable_startup)
    except OSError:
        # Startup registration is optional. The Settings control remains the
        # visible recovery path if the session temporarily denies access.
        pass
    window = MainWindow(
        controller,
        {provider.provider_id: provider for provider in providers},
        startup,
    )
    restore_upgrade_draft(window, controller.settings, app_data_root() / "upgrade-ui-draft.json")
    shell = DesktopShell(window)
    activation_channel.activation_requested.connect(shell.restore_window)
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    application.setQuitOnLastWindowClosed(not tray_available)
    application._sentinel_window = window  # type: ignore[attr-defined]
    application._sentinel_shell = shell  # type: ignore[attr-defined]
    application._sentinel_instance_guard = instance_guard  # type: ignore[attr-defined]
    application._sentinel_activation_channel = activation_channel  # type: ignore[attr-defined]
    if not args.background or not tray_available:
        window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

