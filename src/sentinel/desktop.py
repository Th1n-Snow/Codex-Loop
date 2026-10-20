"""PySide6 desktop shell, navigation, background work, and tray lifecycle."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import time
from typing import Callable

from PySide6.QtCore import (
    QEvent,
    QObject,
    QRunnable,
    QTime,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .app_controller import ApplicationController
from .activity import RecentStartsDialog
from .app_state import (
    AppSettings,
    ProviderViewState,
    automation_decision,
    format_countdown,
)
from .chain import WEEKLY_PROTECTION_PERCENT
from .branding import make_app_icon, render_mark
from .host import platform_label
from .product import PRODUCT
from .presentation import operational_presentation
from .self_test import SelfTestResult, self_test_message
from .appointments import BackgroundAppointments
from .auto_sync import UsageAutoSync
from .appearance import AppearanceManager, AppearancePanel
from .provider_runtime import ProviderOperationResult
from .providers import CompatibilityResult
from .schedule import DAILY, WEEKLY, MULTI, schedule_summary
from .multi_time_ui import MultiTimePanel
from .diagnostics import technical_summary
from .history import HistoryStateError
from .ui_components import (
    Disclosure,
    ElidingLabel,
    ProviderCard,
    ScheduleCard,
    StatusPill,
    TimeEntry,
    ToggleSwitch,
    daily_schedule_example,
    make_surface_card,
    present_provider_state,
    weekly_schedule_preview_details,
    pause_until_text,
    automatic_start_history_copy,
)
from .ui_theme import desktop_stylesheet
from .update_ui import UpdatePanel
from .updates import GitHubReleaseUpdater


class WorkerSignals(QObject):
    completed = Signal(str, object)
    failed = Signal(str, str)


class OperationWorker(QRunnable):
    def __init__(self, provider_id: str, operation: Callable[[], object]):
        super().__init__()
        self.provider_id = provider_id
        self.operation = operation
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.operation()
        except Exception as exc:
            category = getattr(exc, "category", "unexpected_error")
            self.signals.failed.emit(self.provider_id, str(category))
            return
        self.signals.completed.emit(self.provider_id, result)


def tray_tooltip_text(
    settings: AppSettings,
    state: ProviderViewState | None,
    *,
    now: float,
    persistence_error: str | None = None,
) -> str:
    """Summarize cached dashboard state without exposing implementation labels."""
    return operational_presentation(settings, state, now=now,
                                    persistence_error=persistence_error).tray_text


class MainWindow(QMainWindow):
    PAGE_NAMES = ("Dashboard", "Settings", "About")
    tray_tooltip_changed = Signal(str)
    presentation_changed = Signal()
    notification_requested = Signal(str, str)

    def __init__(
        self,
        controller: ApplicationController,
        providers: dict[str, object],
        startup_manager: object,
        *,
        updater: GitHubReleaseUpdater | None = None,
        confirm_enable: Callable[[], bool] | None = None,
        confirm_bootstrap: Callable[[], bool] | None = None,
        confirm_install: Callable[[str], bool] | None = None,
        platform_name: str | None = None,
    ):
        super().__init__()
        self.controller = controller
        self.providers = providers
        self.startup_manager = startup_manager
        self.platform_name = platform_name or platform_label()
        self.is_windows = self.platform_name == "Windows"
        self.confirm_enable = confirm_enable or self._confirm_enable
        self.confirm_bootstrap = confirm_bootstrap or self._confirm_bootstrap
        self.active_operations: dict[str, str] = {}
        self._automatic_syncs: set[str] = set()
        self.usage_auto_sync = UsageAutoSync(self)
        self._verification_context: dict[str, tuple[ProviderViewState, float]] = {}
        self.appointments = BackgroundAppointments(controller,
            lambda pid, mode, slot: self._start_operation(pid, mode, scheduled_at=slot),
            self._prepare_connection, lambda: self.active_operations)

        self._probe_context: dict[str, tuple[ProviderViewState, ProviderViewState, bool]] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.hide_on_close = False
        self.force_close = False
        self.current_tray_tooltip = PRODUCT.display_name
        self._last_history_signature = None

        self.appearance_manager = AppearanceManager(self, controller.settings)
        self.setWindowTitle(PRODUCT.display_name)
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(720, 560)
        self.resize(1040, 720)
        self.setStyleSheet(desktop_stylesheet())

        app_root = QWidget()
        app_root.setObjectName("appRoot")
        shell = QVBoxLayout(app_root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_header())

        self.pages = QStackedWidget()
        self.provider_cards: dict[str, ProviderCard] = {}
        self.pages.addWidget(self._build_dashboard())
        self.pages.addWidget(
            self._build_settings(updater or GitHubReleaseUpdater(), confirm_install)
        )
        self.pages.addWidget(self._build_about())
        shell.addWidget(self.pages, 1)
        shell.addWidget(self._build_footer())
        self.setCentralWidget(app_root)

        self.appearance_manager.apply_theme(self.controller.settings.theme_mode)
        self.automation_toggle.toggled.connect(self._automation_toggled)
        self.dashboard_automation_toggle.toggled.connect(
            self._automation_toggled
        )
        self.schedule_card.pause_button.clicked.connect(self.toggle_temporary_pause)
        self.startup_toggle.toggled.connect(self._startup_toggled)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.refresh_clock)
        self.clock_timer.start(1_000)
        self.automation_timer = QTimer(self)
        self.automation_timer.timeout.connect(self.evaluate_automation)
        self.automation_timer.start(15_000)
        self.refresh_clock()
        self.usage_sync_timer = QTimer(self)
        self.usage_sync_timer.timeout.connect(self._maybe_sync_usage)
        self.usage_sync_timer.start(5_000)

    #: Windows gives a maximized window an invisible resize border that hangs
    #: past each screen edge. Content flush against the layout edge lands under
    #: it and is clipped, so the header keeps a margin wider than that border.
    HEADER_SIDE_MARGIN = 26

    def _build_header(self) -> QWidget:
        """Brand on the left, navigation and trust chip pinned right.

        The brand block is the only elastic item and it is allowed to shrink to
        nothing, so the navigation and chip can never be pushed off the edge no
        matter how narrow or wide the window gets.
        """
        header = QFrame()
        header.setObjectName("appHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(self.HEADER_SIDE_MARGIN, 12, self.HEADER_SIDE_MARGIN, 12)
        layout.setSpacing(16)

        brand = QWidget()
        brand.setObjectName("brandBlock")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(12)
        mark = QLabel()
        # The mark supports the wordmark rather than competing with it.
        mark.setPixmap(render_mark(36))
        mark.setFixedSize(36, 36)
        brand_layout.addWidget(mark)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        wordmark = QHBoxLayout()
        wordmark.setSpacing(0)
        first = QLabel("Codex ")
        first.setObjectName("wordmarkPrimary")
        second = QLabel("Loop")
        second.setObjectName("wordmarkAccent")
        wordmark.addWidget(first)
        wordmark.addWidget(second)
        wordmark.addStretch()
        self.tagline_label = ElidingLabel(PRODUCT.tagline)
        self.tagline_label.setObjectName("appPurpose")
        identity.addLayout(wordmark)
        identity.addWidget(self.tagline_label)
        brand_layout.addLayout(identity, 1)
        # Stretch factor 1 gives the brand every spare pixel, and its own
        # minimum is near zero, so it absorbs the slack and yields it back.
        layout.addWidget(brand, 1)

        controls = QWidget()
        controls.setObjectName("headerControls")
        controls.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        self.nav_buttons: list[QPushButton] = []
        for index, page_name in enumerate(self.PAGE_NAMES):
            button = QPushButton(page_name)
            button.setObjectName("navButton")
            button.setProperty("active", index == 0)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button.clicked.connect(
                lambda checked=False, page_index=index: self.show_page(page_index)
            )
            self.nav_buttons.append(button)
            controls_layout.addWidget(button)

        layout.addWidget(controls, 0)

        self.header_widget = header
        self.header_controls = controls
        self.brand_block = brand
        header.installEventFilter(self)
        return header

    def eventFilter(self, watched, event):
        if watched is getattr(self, "header_widget", None) and event.type() == QEvent.Type.Resize:
            self._fit_header()
        return super().eventFilter(watched, event)

    def _fit_header(self) -> None:
        """Keep navigation reachable and hide the subtitle only when space runs out."""
        header = getattr(self, "header_widget", None)
        if header is None:
            return
        available = header.width() - self.HEADER_SIDE_MARGIN * 2

        # Measure navigation using the current font and accessibility scale.
        brand_floor = self.brand_block.minimumSizeHint().width()
        spacing = 6
        nav_cost = sum(button.sizeHint().width() for button in self.nav_buttons)
        nav_cost += spacing * max(0, len(self.nav_buttons) - 1)
        used = brand_floor + nav_cost
        # The tagline is the first thing to go; it is decoration, not navigation.
        self.tagline_label.setVisible(available - used >= 60)

    def _build_footer(self) -> QWidget:
        """A quiet status strip carrying only the current version."""
        footer = QFrame()
        footer.setObjectName("appFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(self.HEADER_SIDE_MARGIN, 9, self.HEADER_SIDE_MARGIN, 9)
        layout.setSpacing(12)
        layout.addStretch(1)
        version = QLabel(f"{PRODUCT.display_name} v{PRODUCT.version}")
        version.setObjectName("footerVersion")
        version.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(version, 0)
        self.footer_widget = footer
        return footer

    def _page(
        self, title: str, intro: str
    ) -> tuple[QScrollArea, QVBoxLayout, QLabel]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMaximumWidth(1260)
        content.setMinimumWidth(560)
        root = QVBoxLayout(content)
        root.setContentsMargins(34, 24, 34, 28)
        root.setSpacing(14)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        intro_label = QLabel(intro)
        intro_label.setObjectName("pageIntro")
        intro_label.setWordWrap(True)
        root.addWidget(title_label)
        root.addWidget(intro_label)
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addStretch()
        wrapper_layout.addWidget(content, 1)
        wrapper_layout.addStretch()
        scroll.setWidget(wrapper)
        return scroll, root, intro_label

    def _build_dashboard(self) -> QWidget:
        page, root, self.dashboard_intro = self._page(
            "Your Codex reset clock",
            "If Codex reports a 5-hour window, using it starts the next reset clock. With this PC awake, "
            "Codex Loop can start the next one while you’re away, so it is already counting down when you return.",
        )
        self.dashboard_clarifier = QLabel(
            "Codex Loop does not add quota or bypass limits. It uses one minimal request to start "
            "your normal next window."
        )
        self.dashboard_clarifier.setProperty("muted", True)
        self.dashboard_clarifier.setWordWrap(True)
        root.addWidget(self.dashboard_clarifier)
        overall = QFrame()
        overall.setObjectName("overallStatusCard")
        overall_layout = QHBoxLayout(overall)
        overall_layout.setContentsMargins(22, 17, 22, 17)
        overall_layout.setSpacing(16)
        self.overall_icon = QLabel("✓")
        self.overall_icon.setObjectName("overallIcon")
        self.overall_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_icon.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.overall_icon.setFixedSize(30, 30)
        overall_layout.addWidget(self.overall_icon)
        overall_copy = QVBoxLayout()
        overall_copy.setSpacing(3)
        self.overall_title = QLabel()
        self.overall_title.setObjectName("overallTitle")
        self.overall_detail = QLabel()
        self.overall_detail.setProperty("muted", True)
        self.overall_detail.setWordWrap(True)
        overall_copy.addWidget(self.overall_title)
        overall_copy.addWidget(self.overall_detail)
        self.recheck_dashboard_button = QPushButton("Recheck Codex compatibility")
        self.recheck_dashboard_button.setObjectName("secondaryButton")
        self.recheck_dashboard_button.clicked.connect(self.recheck_compatibility)
        overall_copy.addWidget(self.recheck_dashboard_button, 0, Qt.AlignmentFlag.AlignLeft)
        overall_layout.addLayout(overall_copy, 1)
        self.automation_state_label = StatusPill()
        self.automation_state_label.setFixedHeight(28)
        overall_layout.addWidget(self.automation_state_label)
        root.addWidget(overall)
        self.multi_time_panel = MultiTimePanel(self.controller.settings)
        self.multi_time_panel.saved.connect(self._save_multi_times)
        root.addWidget(self.multi_time_panel)

        provider_row = QHBoxLayout()
        provider_row.setSpacing(16)
        for provider_id, state in self.controller.states.items():
            card = ProviderCard(state)
            card.action_button.clicked.connect(
                lambda checked=False, key=provider_id: self.start_bootstrap(key)
            )
            card.sync_button.clicked.connect(
                lambda checked=False, key=provider_id: self.start_usage_sync(key)
            )
            card.verify_button.clicked.connect(
                lambda checked=False, key=provider_id: self.start_window_verification(key)
            )
            card.update_button.clicked.connect(
                lambda checked=False: self._check_updates_for_model_support()
            )
            self.provider_cards[provider_id] = card
            provider_row.addWidget(card, 1)
        self.schedule_card = ScheduleCard()
        self.dashboard_automation_toggle = self.schedule_card.automation_toggle
        self.schedule_card.manage_button.setText("编辑预热时间")
        self.schedule_card.manage_button.clicked.connect(self._focus_multi_times)
        self.last_action_label = self.schedule_card.last_action_label
        self.schedule_card.history_button.clicked.connect(self.show_recent_starts)
        provider_row.addWidget(self.schedule_card, 1)
        root.addLayout(provider_row)

        weekly = QFrame()
        weekly.setObjectName("weeklySafetyCard")
        weekly_layout = QVBoxLayout(weekly)
        weekly_layout.setContentsMargins(20, 14, 20, 14)
        weekly_layout.setSpacing(8)
        weekly_header = QHBoxLayout()
        weekly_title = QLabel("Weekly allowance")
        weekly_title.setObjectName("providerName")
        weekly_header.addWidget(weekly_title)
        weekly_header.addStretch()
        self.weekly_status = StatusPill()
        weekly_header.addWidget(self.weekly_status)
        weekly_layout.addLayout(weekly_header)
        weekly_metrics = QHBoxLayout()
        weekly_metrics.setSpacing(14)
        self.weekly_value = QLabel()
        self.weekly_value.setObjectName("weeklyValue")
        weekly_metrics.addWidget(self.weekly_value)
        self.weekly_detail = QLabel()
        self.weekly_detail.setProperty("muted", True)
        weekly_metrics.addWidget(self.weekly_detail, 1, Qt.AlignmentFlag.AlignVCenter)
        weekly_layout.addLayout(weekly_metrics)
        self.weekly_bar = QProgressBar()
        self.weekly_bar.setObjectName("weeklyBar")
        self.weekly_bar.setRange(0, 100)
        self.weekly_bar.setTextVisible(False)
        self.weekly_bar.setFixedHeight(6)
        weekly_layout.addWidget(self.weekly_bar)
        root.addWidget(weekly)

        # A little slack above and more below reads as deliberate spacing
        # rather than content stranded at the top of a tall window.
        root.addStretch(1)
        return page

    def _build_assurance_strip(self) -> QWidget:
        """The three promises a new user has to understand, kept to one glance."""
        strip = QFrame()
        strip.setObjectName("assuranceStrip")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(22, 15, 22, 15)
        layout.setSpacing(26)
        points = (
            ("Safe and private", "Codex keeps its own sign-in. Codex Loop never reads credentials."),
            ("Local and lightweight", "Countdowns move on this PC with no Codex polling."),
            ("Quota protected", "Weekly allowance is checked, and unclear requests are never retried."),
        )
        for title, body in points:
            column = QVBoxLayout()
            column.setSpacing(4)
            heading = QLabel(title)
            heading.setObjectName("assuranceTitle")
            heading.setWordWrap(True)
            detail = QLabel(body)
            detail.setObjectName("assuranceBody")
            detail.setWordWrap(True)
            # A wrapped label otherwise reports its full single-line width as a
            # minimum, which would push the window past a 1366 pixel display.
            for label in (heading, detail):
                label.setMinimumWidth(140)
                label.setSizePolicy(
                    QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
                )
            column.addWidget(heading)
            column.addWidget(detail)
            column.addStretch()
            layout.addLayout(column, 1)
        return strip

    def _theme_selected(self, mode: str) -> None:
        if self.controller.set_display_preferences(theme_mode=mode):
            self.appearance_manager.apply_theme(mode)
            self.appearance_panel.saved()
        else:
            self.appearance_panel.failed(self.controller.settings)

    def _language_selected(self, language: str) -> None:
        if self.controller.set_display_preferences(ui_language=language):
            self.appearance_manager.apply_language(language)
            self.appearance_panel.saved()
        else:
            self.appearance_panel.failed(self.controller.settings)

    def _build_settings(
        self,
        updater: GitHubReleaseUpdater,
        confirm_install: Callable[[str], bool] | None,
    ) -> QWidget:
        page, root, _intro = self._page(
            "Settings",
            "Choose how Codex Loop keeps your reset clock running.",
        )

        self.appearance_panel = AppearancePanel(self.controller.settings)
        self.appearance_panel.theme_selected.connect(self._theme_selected)
        self.appearance_panel.language_selected.connect(self._language_selected)
        root.addWidget(self.appearance_panel)

        automation_card, automation_layout = make_surface_card(
            "Automation",
            "Codex Loop sends no window-start request while this is off.",
        )
        automation_row = QFrame()
        automation_row.setObjectName("settingRow")
        automation_row_layout = QHBoxLayout(automation_row)
        automation_row_layout.setContentsMargins(14, 12, 14, 12)
        automation_copy = QVBoxLayout()
        self.automation_title_label = QLabel("Keep my 5-hour windows ready")
        self.automation_title_label.setObjectName("secondaryMetric")
        automation_hint = QLabel(
            "Sends one tiny request to Codex, only when a new window needs to start."
        )
        automation_hint.setProperty("muted", True)
        automation_hint.setWordWrap(True)
        automation_copy.addWidget(self.automation_title_label)
        automation_copy.addWidget(automation_hint)
        automation_row_layout.addLayout(automation_copy, 1)
        self.automation_toggle = ToggleSwitch()
        self.automation_toggle.setAccessibleName("Keep my 5-hour windows ready")
        self.automation_toggle.setChecked(self.controller.settings.automation_enabled)
        automation_row_layout.addWidget(self.automation_toggle)
        automation_layout.addWidget(automation_row)

        startup_card, startup_layout = make_surface_card(
            f"{self.platform_name} startup",
            (
                "Start in the tray when you sign in to Windows. Applies to your account only, needs no "
                "administrator rights, and is off until you turn it on."
                if self.is_windows
                else "Start when you sign in to your desktop session. This writes one per-user "
                "autostart entry, needs no root, and is off until you turn it on."
            ),
        )
        startup_row = QFrame()
        startup_row.setObjectName("settingRow")
        row_layout = QHBoxLayout(startup_row)
        row_layout.setContentsMargins(14, 12, 14, 12)
        row_copy = QVBoxLayout()
        row_copy.setSpacing(2)
        startup_label = f"Start {PRODUCT.display_name} with {self.platform_name}"
        row_title = QLabel(startup_label)
        row_title.setObjectName("secondaryMetric")
        row_hint = QLabel(
            "Opens quietly in the tray, not on screen"
            if self.is_windows
            else "Uses the tray if your desktop has one"
        )
        row_hint.setProperty("muted", True)
        row_copy.addWidget(row_title)
        row_copy.addWidget(row_hint)
        row_layout.addLayout(row_copy)
        row_layout.addStretch()
        self.startup_toggle = ToggleSwitch()
        self.startup_toggle.setAccessibleName(startup_label)
        self.startup_toggle.setChecked(bool(self.startup_manager.is_enabled()))
        row_layout.addWidget(self.startup_toggle)
        startup_layout.addWidget(startup_row)

        technical_card, technical_layout = make_surface_card(
            "Codex connection",
            "只读检查本机 Codex 的连接、额度数据和可用轻量模型，约需 30 秒。不会发送预热请求；检查通过也不保证后续网络请求一定成功。",
        )
        self.compatibility_status = QLabel()
        self.compatibility_status.setWordWrap(True)
        technical_layout.addWidget(self.compatibility_status)
        self.recheck_button = QPushButton("Recheck Codex compatibility")
        self.recheck_button.setObjectName("secondaryButton")
        self.recheck_button.clicked.connect(self.recheck_compatibility)
        technical_layout.addWidget(self.recheck_button)
        technical = Disclosure("Technical details")
        self.diagnostic_text = QLabel()
        self.diagnostic_text.setObjectName("diagnosticValue")
        self.diagnostic_text.setWordWrap(True)
        self.diagnostic_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        technical.add_widget(self.diagnostic_text)
        privacy_note = QLabel(
            "Safe to paste into a bug report. No prompts, responses, credentials, or "
            "account identity are ever recorded."
        )
        privacy_note.setProperty("muted", True)
        privacy_note.setWordWrap(True)
        technical.add_widget(privacy_note)
        self.copy_summary_button = QPushButton("Copy this summary")
        self.copy_summary_button.clicked.connect(self._copy_diagnostics)
        technical.add_widget(self.copy_summary_button)
        technical_layout.addWidget(technical)

        # Both hosts get the same user-initiated check. Only the final step
        # differs: Windows runs a verified setup executable, Linux replaces its
        # per-user bundle through the installer that shipped inside it.
        self.update_panel = UpdatePanel(
            updater,
            confirm_install=confirm_install,
            parent=self,
            platform_name=self.platform_name,
        )
        self.update_panel.installer_launched.connect(self._exit_for_update)
        updates_widget: QWidget = self.update_panel
        self.updates_widget = updates_widget
        updates_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        technical_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )

        self.settings_top_row = QWidget()
        top_layout = QHBoxLayout(self.settings_top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(14)
        top_layout.addWidget(automation_card, 1)
        top_layout.addWidget(startup_card, 1)
        root.addWidget(self.settings_top_row)

        self.settings_bottom_row = QWidget()
        bottom_layout = QHBoxLayout(self.settings_bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(14)
        bottom_layout.addWidget(self.updates_widget, 1, Qt.AlignmentFlag.AlignTop)
        bottom_layout.addWidget(technical_card, 1, Qt.AlignmentFlag.AlignTop)
        root.addWidget(self.settings_bottom_row)
        root.addStretch()
        return page

    def _build_about(self) -> QWidget:
        page, root, _intro = self._page(
            f"About {PRODUCT.display_name}",
            "A small local-first app that keeps your normal Codex reset clock moving.",
        )
        about = QFrame()
        about.setObjectName("aboutHero")
        about_layout = QHBoxLayout(about)
        about_layout.setContentsMargins(24, 22, 24, 22)
        about_layout.setSpacing(26)
        story = QVBoxLayout()
        story.setSpacing(12)
        product_title = QLabel(PRODUCT.display_name)
        product_title.setObjectName("aboutProductTitle")
        story.addWidget(product_title)
        version = QLabel(
            f"Version {PRODUCT.version} \u00b7 {self.platform_name} \u00b7 MIT licensed"
        )
        version.setObjectName("secondaryMetric")
        story.addWidget(version)
        self.about_description = QLabel(
            "If Codex reports a 5-hour window, a new one begins when you use Codex. "
            "If the previous window ends while you’re away, the next reset clock normally waits until "
            "you come back and use Codex again. With this PC awake, Codex Loop can start that next window with one minimal "
            "request, so its reset clock can already be counting down before you return. Codex Loop does "
            "not increase your quota or bypass limits."
        )
        self.about_description.setProperty("muted", True)
        self.about_description.setWordWrap(True)
        self.about_description.setMinimumWidth(320)
        self.about_description.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        story.addWidget(self.about_description)

        self.about_steps: list[QFrame] = []
        for number, title, detail in (
            ("1", "Codex reports a 5-hour window", "The clock begins when Codex is used."),
            ("2", "Codex Loop starts the next one", "One minimal request can begin it while this PC is awake."),
            ("3", "No shortcuts or extra quota", "Your existing limits and weekly protection still apply."),
        ):
            step = QFrame()
            step.setObjectName("aboutStep")
            step_layout = QHBoxLayout(step)
            step_layout.setContentsMargins(12, 9, 12, 9)
            step_layout.setSpacing(12)
            badge = QLabel(number)
            badge.setObjectName("aboutStepNumber")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(28, 28)
            step_copy = QVBoxLayout()
            step_copy.setSpacing(2)
            step_title = QLabel(title)
            step_title.setObjectName("aboutStepTitle")
            step_detail = QLabel(detail)
            step_detail.setProperty("muted", True)
            step_detail.setWordWrap(True)
            step_copy.addWidget(step_title)
            step_copy.addWidget(step_detail)
            step_layout.addWidget(badge)
            step_layout.addLayout(step_copy, 1)
            story.addWidget(step)
            self.about_steps.append(step)
        about_layout.addLayout(story, 3)

        action_panel = QFrame()
        action_panel.setObjectName("aboutActions")
        actions = QVBoxLayout(action_panel)
        actions.setContentsMargins(16, 15, 16, 15)
        actions.setSpacing(8)
        self.about_action_title = QLabel("Project links")
        self.about_action_title.setObjectName("weeklyGroupTitle")
        actions.addWidget(self.about_action_title)
        self.about_link_buttons: dict[str, QPushButton] = {}
        for label, url in (("View source", PRODUCT.github_url),
                           ("Releases", PRODUCT.releases_url),
                           ("Report a problem", PRODUCT.bug_report_url),
                           ("Request a feature", PRODUCT.feature_request_url)):
            button = QPushButton(label)
            button.setObjectName("linkButton")
            button.clicked.connect(lambda checked=False, target=url: QDesktopServices.openUrl(QUrl(target)))
            self.about_link_buttons[label] = button
            actions.addWidget(button)

        star_title = QLabel("Support Codex Loop")
        star_title.setObjectName("secondaryMetric")
        actions.addSpacing(6)
        actions.addWidget(star_title)
        self.star_description = QLabel(
            "A GitHub star helps other Codex users discover the project and lets us know it’s worth "
            "continuing to improve."
        )
        self.star_description.setProperty("muted", True)
        self.star_description.setWordWrap(True)
        actions.addWidget(self.star_description)
        self.star_button = QPushButton("★ Support Codex Loop")
        self.star_button.setObjectName("primaryButton")
        self.star_button.clicked.connect(lambda checked=False: QDesktopServices.openUrl(QUrl(PRODUCT.github_url)))
        actions.addWidget(self.star_button)
        actions.addStretch()
        about_layout.addWidget(action_panel, 2)
        root.addWidget(about)

        support, support_layout = make_surface_card(
            "Codex support",
            "Codex Loop checks that the installed Codex client still supports every action it needs before automation runs.",
        )
        support_status = QLabel(
            "Codex Loop is an independent open-source project. It is not affiliated with, endorsed by, "
            "or sponsored by OpenAI. Codex behavior can evolve, so compatibility is checked by capability "
            "instead of trusting a version string."
        )
        support_status.setProperty("muted", True)
        support_status.setWordWrap(True)
        support_layout.addWidget(support_status)
        privacy, privacy_layout = make_surface_card(
            "Privacy and safety",
            "Codex keeps its own sign-in. Codex Loop never reads tokens, credentials, conversations, "
            "or account identifiers.",
        )
        boundaries = QLabel(
            "\u2022 Codex automation is off until you switch it on\n"
            "\u2022 Update checks run only when you press the button, and never touch your plan\n"
            "\u2022 Countdowns are calculated locally and cause no Codex traffic\n"
            "\u2022 A request whose outcome is unclear is never retried automatically\n"
            "\u2022 Weekly limits are respected before any action is considered"
        )
        boundaries.setObjectName("secondaryMetric")
        boundaries.setWordWrap(True)
        privacy_layout.addWidget(boundaries)
        support_privacy = QHBoxLayout()
        support_privacy.setSpacing(14)
        support_privacy.addWidget(support, 1)
        support_privacy.addWidget(privacy, 1)
        root.addLayout(support_privacy)
        root.addStretch()
        return page

    def show_page(self, index: int) -> None:
        if not 0 <= index < self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
        if index == 1:
            self._update_diagnostics(now=time.time())
        elif index == 0:
            QTimer.singleShot(0, self._maybe_sync_usage)

    def _maybe_sync_usage(self) -> None:
        self.usage_auto_sync.tick(time.time())

    def _check_updates_for_model_support(self) -> None:
        self.show_page(1)
        self.update_panel.start_model_support_check()

    def refresh_clock(self, *, now: float | None = None) -> None:
        current = time.time() if now is None else now
        enabled = self.controller.settings.automation_enabled
        paused = self.controller.settings.pause_active(current)
        self._sync_automation_toggles(enabled)
        self.multi_time_panel.update_status(self.controller.settings, current)
        self.automation_state_label.set_status(
            "PAUSED · ON" if paused else ("ON" if enabled else "OFF"),
            "info" if paused else ("success" if enabled else "neutral"),
        )
        pause_button = self.schedule_card.pause_button
        pause_button.setVisible(
            paused or (self.controller.settings.automation_enabled
                       and self.controller.settings.schedule_mode in {DAILY, WEEKLY, MULTI})
        )
        pause_button.setText("Resume automation" if paused else "Pause until tomorrow")
        pause_button.setEnabled(enabled and not self.active_operations)
        target = self.controller.settings.tomorrow_first_start(current)
        pause_button.setToolTip(
            "Wait for the current operation to finish." if self.active_operations else
            ("Return to your saved schedule." if paused else
             f"Pause until tomorrow's first start: {pause_until_text(target)}" if target is not None else "")
        )
        for provider_id, state in self.controller.states.items():
            operational = operational_presentation(
                self.controller.settings, state, now=current,
                checking=self.active_operations.get(provider_id) == "probe",
                persistence_error=self.controller.persistence_error,
            )
            card = self.provider_cards.get(provider_id)
            if card is not None:
                card.update_state(
                    state, now=current, automation_enabled=enabled,
                    operational=operational,
                )
                card.action_button.setVisible(self._can_start_loop(provider_id, now=current))
                card.verify_button.setEnabled(state.installed and provider_id not in self.active_operations)
        codex = self.controller.states.get("codex")
        if codex is not None:
            operational = operational_presentation(
                self.controller.settings, codex, now=current,
                checking=self.active_operations.get("codex") == "probe",
                persistence_error=self.controller.persistence_error,
            )
            checking = self.active_operations.get("codex") == "probe"
            needs_check = (
                not codex.automation_supported
                or self.controller.settings.compatible_runtime_identities.get("codex") != codex.runtime_identity
            )
            self.recheck_dashboard_button.setVisible(
                codex.installed and needs_check
                and "codex" in self.controller.settings.checked_runtime_identities
            )
            for button in (self.recheck_button, self.recheck_dashboard_button):
                button.setEnabled(codex.installed and not self.active_operations and self.controller.persistence_error is None)
                button.setText("Checking Codex…" if checking else "Recheck Codex compatibility")
            self.compatibility_status.setText(
                "Checking usage and models. Allow about 30 seconds. No model request is sent."
                if checking else
                "Codex is not detected. Install and open Codex, then reopen Codex Loop."
                if not codex.installed else
                codex.detail if needs_check else
                "Compatibility confirmed. Your saved schedule and safety checks still apply."
            )
            self.schedule_card.update_schedule(
                self.controller.settings, codex, now=current,
                next_action=operational.next_action,
            )
            self._set_overall_icon(
                "✓" if operational.tone == "success" else
                "!" if operational.tone == "warning" else "○",
                operational.tone,
            )
            self.overall_title.setText(operational.banner_title)
            self.overall_detail.setText(operational.banner_detail)

            if codex.weekly_used_percent is None:
                self.weekly_value.setText("—")
                self.weekly_detail.setText("Not available in the last read-only sync")
                self.weekly_bar.setValue(0)
                self.weekly_status.set_status("NOT CHECKED", "neutral")
            else:
                try:
                    weekly_reset = (
                        time.strftime(
                            "%a %I:%M %p", time.localtime(codex.weekly_reset_at)
                        ).replace(" 0", " ")
                        if codex.weekly_reset_at is not None
                        else "reset time unavailable"
                    )
                except (OSError, OverflowError, ValueError):
                    weekly_reset = "reset time unavailable"
                self.weekly_detail.setText(
                    f"剩余 {max(0.0, min(100.0, 100.0 - codex.weekly_used_percent)):g}% · 已用 {codex.weekly_used_percent:g}% · 重置于 {weekly_reset}"
                )
                self.weekly_value.setText(f"{max(0.0, min(100.0, 100.0 - codex.weekly_used_percent)):g}%")
                self.weekly_bar.setValue(round(max(0.0, min(100.0, 100.0 - codex.weekly_used_percent))))
                self.weekly_bar.setAccessibleName("每周剩余额度")
                weekly_safe = codex.weekly_used_percent < WEEKLY_PROTECTION_PERCENT
                self.weekly_status.set_status(
                    "SAFE" if weekly_safe else "PROTECTED",
                    "success" if weekly_safe else "warning",
                )
            self._refresh_last_automatic_start(now=current)
            self.schedule_card.fit_wrapped_text()
        self._update_diagnostics(now=current)
        tooltip = operational_presentation(
            self.controller.settings, codex, now=current,
            checking=self.active_operations.get("codex") == "probe",
            persistence_error=self.controller.persistence_error,
        ).tray_text
        if tooltip != self.current_tray_tooltip:
            self.current_tray_tooltip = tooltip
            self.tray_tooltip_changed.emit(tooltip)
        self.presentation_changed.emit()

    def show_recent_starts(self) -> None:
        if not hasattr(self, "recent_starts_dialog"):
            history = getattr(self.providers.get("codex"), "history", None)
            self.recent_starts_dialog = RecentStartsDialog(history, self)
        self.recent_starts_dialog.refresh()
        self.recent_starts_dialog.show()
        self.recent_starts_dialog.raise_()
        self.recent_starts_dialog.activateWindow()

    def _refresh_last_automatic_start(self, *, now: float) -> None:
        history = getattr(self.providers.get("codex"), "history", None)
        if history is None:
            self.last_action_label.setText("Last automatic start: None yet")
            return
        try:
            stat = history.path.stat()
        except FileNotFoundError:
            self._last_history_signature = None
            self.last_action_label.setText("Last automatic start: None yet")
            return
        except OSError:
            self._last_history_signature = None
            self.last_action_label.setText("Last automatic start: History unavailable")
            return
        # Clock ticks need no JSONL reread unless history or the displayed day changed.
        signature = (stat.st_mtime_ns, stat.st_size, datetime.fromtimestamp(now).date())
        if signature != self._last_history_signature:
            self.last_action_label.setText(automatic_start_history_copy(history, now=now))
            self._last_history_signature = signature

    def toggle_temporary_pause(self, *, now: float | None = None) -> None:
        current = time.time() if now is None else now
        # A running worker may already be sending. Never promise a pause mid-flight.
        if self.active_operations or not self.controller.settings.automation_enabled:
            return
        if self.controller.settings.pause_active(current):
            saved = self.controller.resume_automation()
        elif self.controller.settings.tomorrow_first_start(current) is not None:
            saved = self.controller.pause_until_tomorrow(now=current)
        else:
            return
        if not saved:
            self._show_persistence_warning()
        # Resume/expiry only removes the gate. The normal timer evaluates safety.
        self.refresh_clock(now=current)

    def evaluate_automation(self, *, now: float | None = None) -> None:
        current = time.time() if now is None else now
        self.controller.refresh_local_states(exclude=self.active_operations)
        for provider_id in self.controller.expire_compatibility(now=current):
            self._notify_compatibility(provider_id,
                "Codex connection needs attention",
                "Read-only retries ended. Automatic starts remain paused.", kind="terminal")
        for provider_id, state in self.controller.states.items():
            if state.compatibility_incident_id and self.controller.record_blocked_opportunity(
                provider_id, now=current
            ):
                self._notify_compatibility(provider_id,
                    "Scheduled start blocked",
                    "Codex needs a compatibility check. No start was sent.", kind="blocked")
        self.appointments.tick(current)
        for provider_id, decision in self.controller.decisions(now=current).items():
            if provider_id in self.active_operations:
                continue
            if decision.action == "PROBE":
                self._start_operation(provider_id, "probe", automatic=True)
            elif decision.action == "TIMED":
                # Multi-time appointments are admitted and drained by the backend queue.
                continue

    def _can_start_loop(self, provider_id: str, *, now: float) -> bool:
        state = self.controller.states.get(provider_id)
        settings = self.controller.settings
        if state is None:
            return False
        if not operational_presentation(settings, state, now=now,
                                        checking=self.active_operations.get(provider_id) == "probe",
                                        persistence_error=self.controller.persistence_error).manual_start_visible:
            return False
        # A reported reset remains useful for quota timing. It only hides this
        # manual action when the current reading actually proves an anchor.
        current_anchor = (
            state.reset_at is not None and state.reset_at > now
            and (state.quota_state == "ANCHORED" or (
                state.quota_state is None and state.last_verified_at is not None
            ))
        )
        return (
            provider_id == "codex" and settings.automation_enabled
            and not settings.pause_active(now)
            and state.installed and state.automation_supported
            and state.runtime_identity is not None
            and settings.compatible_runtime_identities.get(provider_id) == state.runtime_identity
            and self.controller.persistence_error is None
            and provider_id not in self.active_operations
            and state.status not in {"Starting", "Checking", "Needs attention"}
            and not current_anchor
        )

    def start_bootstrap(self, provider_id: str) -> None:
        if not self._can_start_loop(provider_id, now=time.time()) or not self.confirm_bootstrap():
            return
        if not self._can_start_loop(provider_id, now=time.time()):
            return
        self._start_operation(provider_id, "bootstrap")

    def start_window_verification(self, provider_id: str) -> None:
        if provider_id in self.active_operations:
            return
        state = self.controller.states.get(provider_id)
        card = self.provider_cards.get(provider_id)
        provider = self.providers.get(provider_id)
        if state is None or card is None or provider is None or not state.installed:
            if card is not None:
                card.show_verification_result("未检测到本机 Codex，无法验证。", "warning")
            return
        self._verification_context[provider_id] = (state, time.time())
        self.active_operations[provider_id] = "verify"
        card.start_verification_display()
        worker = OperationWorker(provider_id, lambda: provider.self_test(current_state=state))
        worker.signals.completed.connect(self._window_verification_completed)
        worker.signals.failed.connect(self._window_verification_failed)
        self.thread_pool.start(worker)

    def _window_verification_completed(self, provider_id: str, result: object) -> None:
        action = self.active_operations.pop(provider_id, None)
        context = self._verification_context.pop(provider_id, None)
        card = self.provider_cards.get(provider_id)
        if action != "verify" or context is None or card is None:
            return
        prior, started_at = context
        current = self.controller.states.get(provider_id)
        if (not isinstance(result, SelfTestResult) or current is None
                or current.runtime_identity != prior.runtime_identity):
            card.show_verification_result("Codex 状态发生变化，未采用旧结果；请重新自检。", "warning")
            self.refresh_clock()
            return
        text, tone = self_test_message(result)
        fresh = result.after or result.before
        if fresh is not None and fresh.state.runtime_identity == prior.runtime_identity:
            if not self.controller.apply_sync_result(fresh.state):
                text += "\n本地状态保存失败，请检查存储位置。"
                tone = "warning"
        card.show_verification_result(text, tone)
        self.refresh_clock()

    def _window_verification_failed(self, provider_id: str, _category: str) -> None:
        self.active_operations.pop(provider_id, None)
        self._verification_context.pop(provider_id, None)
        card = self.provider_cards.get(provider_id)
        if card is not None:
            card.show_verification_result("自检异常：未能确认请求结果；不会自动重试。", "warning")
        self.refresh_clock()

    def start_usage_sync(self, provider_id: str, *, automatic: bool = False) -> None:
        if provider_id in self.active_operations:
            return
        provider = self.providers.get(provider_id)
        state = self.controller.states.get(provider_id)
        card = self.provider_cards.get(provider_id)
        if provider is None or state is None or not state.installed:
            if card is not None:
                card.set_sync_state("unavailable")
            return
        self.active_operations[provider_id] = "sync"
        if automatic:
            self._automatic_syncs.add(provider_id)
        if card is not None:
            card.set_sync_state("syncing")
        worker = OperationWorker(
            provider_id,
            lambda: provider.sync_usage(current_state=state),
        )
        worker.signals.completed.connect(self._operation_completed)
        worker.signals.failed.connect(self._operation_failed)
        self.thread_pool.start(worker)

    def recheck_compatibility(self) -> None:
        """One explicit read-only probe; never enable automation or run a turn."""
        if self.active_operations or self.controller.persistence_error is not None:
            return
        self.controller.refresh_local_states()
        state = self.controller.states.get("codex")
        if state is None or not state.installed:
            self.refresh_clock()
            return
        self._start_operation("codex", "probe")

    def _start_operation(self, provider_id: str, action: str, *, automatic: bool = False, scheduled_at: float | None = None) -> None:
        provider = self.providers.get(provider_id)
        if provider is None:
            return
        state = self.controller.states[provider_id]
        pending = replace(state, status="Checking" if action == "probe" else "Starting",
                          detail="Checking Codex safely.")
        saved = self.controller.update_provider_state(
            pending
        )
        if not saved:
            self.refresh_clock()
            return
        self.active_operations[provider_id] = action
        if action == "probe":
            self._probe_context[provider_id] = (state, pending, automatic)
        operation = (
            provider.probe
            if action == "probe"
            else lambda: (provider.run_action(action, current_state=state) if scheduled_at is None
                          else provider.run_action(action, current_state=state, scheduled_at=scheduled_at))
        )
        worker = OperationWorker(provider_id, operation)
        worker.signals.completed.connect(self._operation_completed)
        worker.signals.failed.connect(self._operation_failed)
        self.thread_pool.start(worker)
        self.refresh_clock()

    def _prepare_connection(self, provider_id: str, runtime_identity: str) -> None:
        provider = self.providers.get(provider_id)
        if provider_id in self.active_operations or not hasattr(provider, "prepare_connection"):
            return
        self.active_operations[provider_id] = "prepare"
        worker = OperationWorker(provider_id, lambda: provider.prepare_connection(runtime_identity=runtime_identity))
        worker.signals.completed.connect(self._connection_prepared)
        worker.signals.failed.connect(lambda pid, category: self._connection_prepared(pid, False))
        self.thread_pool.start(worker)

    def _connection_prepared(self, provider_id: str, _result: object) -> None:
        if self.active_operations.get(provider_id) == "prepare":
            self.active_operations.pop(provider_id, None)
        settings = self.controller.settings
        if not settings.automation_enabled or settings.pause_active(time.time()):
            provider = self.providers.get(provider_id)
            if hasattr(provider, "discard_prepared"):
                provider.discard_prepared()
        self.refresh_clock()

    def _probe_runtime_is_current(self, provider_id: str, expected_identity: str | None) -> bool:
        """Recheck the local executable after an in-flight compatibility probe."""
        try:
            detected = self.providers[provider_id].detect()
        except Exception:
            return False
        if detected.runtime_identity != expected_identity:
            self.controller.refresh_local_states()
            return False
        return True

    def _operation_completed(self, provider_id: str, result: object) -> None:
        action = self.active_operations.pop(provider_id, None)
        automatic_sync = provider_id in self._automatic_syncs
        self._automatic_syncs.discard(provider_id)
        if automatic_sync:
            success = (isinstance(result, ProviderOperationResult)
                       and result.outcome == 'SYNC_UPDATED'
                       and result.state.runtime_identity == self.controller.states[provider_id].runtime_identity)
            self.usage_auto_sync.finished(time.time(), success=success)
            if not success:
                self.provider_cards[provider_id].set_sync_state('inconclusive')
                self.refresh_clock()
                return
        if isinstance(result, CompatibilityResult):
            context = self._probe_context.pop(provider_id, None)
            if action != "probe" or context is None:
                self.refresh_clock()
                return
            prior, pending, automatic = context
            if not self._probe_runtime_is_current(provider_id, pending.runtime_identity):
                if self.controller.states[provider_id] == pending:
                    self.controller.update_provider_state(prior)
                self.refresh_clock()
                return
            current = self.controller.states[provider_id]
            if (current != pending or result.runtime_identity != pending.runtime_identity or
                    (automatic and (not self.controller.settings.automation_enabled
                                    or self.controller.settings.pause_active(time.time())))):
                if current == pending:
                    self.controller.update_provider_state(prior)
                self.refresh_clock()
                return
            notified = prior.compatibility_notified
            saved = self.controller.apply_compatibility(provider_id, result,
                                                          explicit=not automatic)
            if saved and result.compatible and notified:
                self.notification_requested.emit("Codex connection restored",
                    "Codex Loop can follow the saved schedule again. Safety checks still apply.")
            elif saved and not result.compatible and self.controller.states[provider_id].compatibility_next_retry_at is None:
                self._notify_compatibility(provider_id, "Codex connection needs attention",
                    "Automatic starts are paused. Recheck Codex when ready.", kind="terminal")
        elif isinstance(result, ProviderOperationResult):
            if result.state.runtime_identity != self.controller.states[provider_id].runtime_identity:
                self.refresh_clock()
                return
            if action == "sync":
                saved = self.controller.apply_sync_result(result.state)
            else:
                self.controller.apply_operation_result(
                    result.outcome, result.state, now=time.time()
                )
            if action == "sync":
                self.provider_cards[provider_id].set_sync_state(
                    "updated"
                    if saved and result.outcome == "SYNC_UPDATED"
                    else "inconclusive"
                )
        else:
            if action == "probe":
                self._probe_context.pop(provider_id, None)
            self.refresh_clock()
            return
        self.refresh_clock()

    def _operation_failed(self, provider_id: str, category: str) -> None:
        action = self.active_operations.pop(provider_id, None)
        if provider_id in self._automatic_syncs:
            self._automatic_syncs.discard(provider_id)
            self.usage_auto_sync.finished(time.time(), success=False)
        if action == "probe":
            context = self._probe_context.pop(provider_id, None)
            if context is None:
                self.refresh_clock()
                return
            prior, pending, automatic = context
            if not self._probe_runtime_is_current(provider_id, pending.runtime_identity):
                if self.controller.states[provider_id] == pending:
                    self.controller.update_provider_state(prior)
                self.refresh_clock()
                return
            current = self.controller.states[provider_id]
            if (current == pending and
                    (not automatic or (self.controller.settings.automation_enabled
                                       and not self.controller.settings.pause_active(time.time())))):
                failure = CompatibilityResult(False, "Needs attention",
                    "The Codex compatibility check stopped safely. No request was sent.",
                    prior.runtime_identity or "unavailable", failure_category=category)
                if self.controller.apply_compatibility(provider_id, failure, explicit=not automatic):
                    if self.controller.states[provider_id].compatibility_next_retry_at is None:
                        self._notify_compatibility(provider_id, "Codex connection needs attention",
                            "Automatic starts are paused. Recheck Codex when ready.", kind="terminal")
            elif current == pending:
                self.controller.update_provider_state(prior)
            self.refresh_clock()
            return
        if action == "sync":
            card = self.provider_cards.get(provider_id)
            if card is not None:
                card.set_sync_state("inconclusive")
            self.refresh_clock()
            return
        state = self.controller.states[provider_id]
        self.controller.update_provider_state(
            replace(
                state,
                status="Needs attention",
                detail=f"The check stopped safely ({category}). Nothing was retried. See Settings for detail.",
            )
        )
        self.refresh_clock()

    def _notify_compatibility(self, provider_id: str, title: str, message: str, *, kind: str) -> None:
        if self.controller.mark_compatibility_notified(provider_id, kind=kind):
            self.notification_requested.emit(title, message)

    def _automation_toggled(self, enabled: bool) -> None:
        if enabled and not self.confirm_enable():
            self._sync_automation_toggles(False)
            return
        if not self.controller.set_automation_enabled(enabled):
            self._sync_automation_toggles(
                self.controller.settings.automation_enabled
            )
            self._show_persistence_warning()
            self.refresh_clock()
            return
        self.refresh_clock()
        if enabled:
            self.evaluate_automation()

    def _sync_automation_toggles(self, enabled: bool) -> None:
        for toggle in (
            self.automation_toggle,
            self.dashboard_automation_toggle,
        ):
            toggle.blockSignals(True)
            toggle.setChecked(enabled)
            toggle.blockSignals(False)

    def _set_overall_icon(self, glyph: str, tone: str) -> None:
        self.overall_icon.setText(glyph)
        self.overall_icon.setProperty("tone", tone)
        self.overall_icon.style().unpolish(self.overall_icon)
        self.overall_icon.style().polish(self.overall_icon)

    def _startup_toggled(self, enabled: bool) -> None:
        previous = self.controller.settings.start_with_windows
        try:
            self.startup_manager.set_enabled(enabled)
        except OSError:
            self.startup_toggle.blockSignals(True)
            self.startup_toggle.setChecked(not enabled)
            self.startup_toggle.blockSignals(False)
            QMessageBox.warning(
                self,
                "Startup setting not changed",
                f"{self.platform_name} did not allow the per-user startup setting to be changed.",
            )
            return
        if not self.controller.set_start_with_windows(enabled):
            try:
                self.startup_manager.set_enabled(previous)
            except OSError:
                pass
            self.startup_toggle.blockSignals(True)
            self.startup_toggle.setChecked(previous)
            self.startup_toggle.blockSignals(False)
            self._show_persistence_warning()
            self.refresh_clock()


    def _focus_multi_times(self) -> None:
        self.show_page(0)
        self.pages.widget(0).ensureWidgetVisible(self.multi_time_panel)
        if self.multi_time_panel.editors:
            self.multi_time_panel.editors[0].setFocus()

    def _save_multi_times(self, values) -> None:
        try:
            saved = self.controller.set_multi_start_times(values)
        except ValueError as exc:
            self.multi_time_panel.show_save_error(str(exc))
            QMessageBox.information(self, "预热时间", str(exc))
            return
        if not saved:
            self.multi_time_panel.show_save_error("保存失败，时间表未更改。")
            self._show_persistence_warning()
            return
        self.multi_time_panel.set_times(self.controller.settings.multi_start_times)
        self.refresh_clock()
        self.multi_time_panel.show_save_success(self.controller.settings)
        self.evaluate_automation()








    def _show_persistence_warning(self) -> None:
        QMessageBox.warning(
            self,
            "Setting not saved",
            "Codex Loop could not save that setting, so it was changed back. Automatic starts are paused until local state can be written again.",
        )

    def _update_diagnostics(self, *, now: float) -> None:
        events = ()
        history = self.controller.error_history
        if self.pages.currentIndex() == 1 and history is not None:
            reader = getattr(history, "recent_compatibility_events", None)
            if callable(reader):
                try:
                    events = reader(limit=10)
                except (HistoryStateError, OSError):
                    events = ()
        self.diagnostic_text.setText(
            technical_summary(
                self.controller.states,
                self.controller.settings,
                persistence_error=self.controller.persistence_error is not None,
                compatibility_events=events,
            )
        )

    def _copy_diagnostics(self, _checked: bool = False) -> None:
        try:
            clipboard = QApplication.clipboard()
            if clipboard is None:
                raise RuntimeError("The desktop clipboard is unavailable")
            clipboard.setText(self.diagnostic_text.text())
        except Exception:
            self.copy_summary_button.setText("Copy failed")
            QMessageBox.warning(
                self,
                "Summary not copied",
                f"{self.platform_name} did not allow Codex Loop to copy the diagnostic summary. "
                "Try again after closing other clipboard tools.",
            )
            return
        self.copy_summary_button.setText("Copied")
        QTimer.singleShot(
            2_000,
            lambda: self.copy_summary_button.setText("Copy this summary"),
        )

    def _exit_for_update(self) -> None:
        application = QApplication.instance()
        if application is None:
            self.update_panel._operation_failed(
                "install",
                "The installer started, but Codex Loop could not close automatically. Close it before continuing setup.",
            )
            return
        try:
            QTimer.singleShot(200, application.quit)
        except Exception:
            self.update_panel._operation_failed(
                "install",
                "The installer started, but Codex Loop could not close automatically. Close it before continuing setup.",
            )
            return
        self.force_close = True

    def _confirm_enable(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Keep your Codex reset clock running?",
            f"{PRODUCT.display_name} will use your signed-in Codex client only after its safety checks "
            "pass. It checks weekly allowance, sends one minimal request, then verifies the reset.\n\n"
            "Starting a window uses a small amount of your plan. An action "
            "whose outcome is unclear is never retried.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _confirm_bootstrap(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Start my first window now?",
            "Codex Loop first checks quota without spending it. Only if no window is running and "
            "the safety checks pass will it send one small request and verify the reset clock. "
            "Your chosen routine then takes over. An unclear start is not retried.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        return answer == QMessageBox.StandardButton.Yes

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.hide_on_close and not self.force_close:
            self.hide()
            event.ignore()
            return
        event.accept()


class DesktopShell:
    def __init__(self, window: MainWindow):
        self.window = window
        self.tray = QSystemTrayIcon(make_app_icon(), window)
        self.tray.setToolTip(window.current_tray_tooltip)
        self.window.tray_tooltip_changed.connect(self.tray.setToolTip)
        self.window.notification_requested.connect(self.tray.showMessage)
        menu = QMenu()
        self.status_action = menu.addAction(window.current_tray_tooltip)
        self.status_action.setEnabled(False)
        self.pause_action = menu.addAction("Pause until tomorrow's first start")
        self.pause_action.triggered.connect(window.toggle_temporary_pause)
        menu.addSeparator()
        open_action = menu.addAction(f"Open {PRODUCT.display_name}")
        open_action.triggered.connect(self.restore_window)
        self.history_action = menu.addAction("Recent starts")
        self.history_action.triggered.connect(window.show_recent_starts)
        menu.addSeparator()
        quit_action = menu.addAction(f"Quit {PRODUCT.display_name}")
        quit_action.triggered.connect(self.quit)
        self.tray.setContextMenu(menu)
        menu.aboutToShow.connect(self.refresh_menu)
        self.window.presentation_changed.connect(self.refresh_menu)
        self.refresh_menu()
        self.tray.activated.connect(self._tray_activated)
        # A GNOME session without a status-notifier extension has no tray at
        # all. Showing an icon nothing can render would leave Pause, Recent
        # starts, and Quit unreachable, so the window becomes the only surface
        # and closing it exits instead of hiding into nothing.
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.window.hide_on_close = self.tray_available
        application = QApplication.instance()
        if application is not None:
            application.aboutToQuit.connect(self.tray.hide)
        if self.tray_available:
            self.tray.show()

    def refresh_menu(self, *, now: float | None = None) -> None:
        current = time.time() if now is None else now
        settings = self.window.controller.settings
        paused = settings.pause_active(current)
        self.status_action.setText(tray_tooltip_text(
            settings, self.window.controller.states.get("codex"), now=current,
            persistence_error=self.window.controller.persistence_error,
        ))
        target = settings.tomorrow_first_start(current)
        self.pause_action.setVisible(paused or target is not None)
        self.pause_action.setText(
            "Resume automation" if paused else
            f"Pause until {pause_until_text(target)}" if target is not None else
            "Pause until tomorrow's first start"
        )
        self.pause_action.setEnabled(settings.automation_enabled and not self.window.active_operations)

    def hide_window(self) -> None:
        self.window.hide()

    def restore_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def quit(self) -> None:
        self.window.force_close = True
        self.tray.hide()
        self.window.close()
        application = QApplication.instance()
        if application is not None:
            application.quit()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in {
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        }:
            self.restore_window()
