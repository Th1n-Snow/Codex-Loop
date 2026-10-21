"""Central design tokens and Qt styling for the desktop shell."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThemeTokens:
    background: str = "#0A111C"
    background_deep: str = "#070D16"
    surface: str = "#101B29"
    surface_sunken: str = "#0C1522"
    surface_raised: str = "#16222F"
    surface_hover: str = "#1B283A"
    border: str = "#253449"
    border_strong: str = "#33465E"
    text: str = "#EDF3FA"
    text_soft: str = "#C2CEDC"
    text_muted: str = "#8B99AA"
    text_faint: str = "#6B7A8C"
    accent: str = "#22D3A1"
    accent_deep: str = "#10B981"
    accent_hover: str = "#22D3A1"
    accent_ink: str = "#04150E"
    progress_fill: str | None = None
    progress_track: str | None = None
    secondary_ink: str | None = None
    secondary_surface: str | None = None
    header_surface: str | None = None
    banner_surface: str | None = None
    nav_surface: str | None = None
    secondary_border: str | None = None
    badge_surface: str | None = None
    info: str = "#74C4FF"
    warning: str = "#F1D38A"
    error: str = "#FFB4AE"
    radius_small: int = 8
    radius: int = 12
    radius_large: int = 16
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 24
    space_6: int = 32
    font_family: str = "Segoe UI Variable, Segoe UI"


DARK_TOKENS = ThemeTokens()
LIGHT_TOKENS = ThemeTokens(
    background="#F5F7F5", background_deep="#EEF3F0", surface="#FFFFFF",
    surface_sunken="#EDF3F0", surface_raised="#F1F6F3", surface_hover="#E2EDE7",
    border="#D8E3DE", border_strong="#B8CEC2", text="#1E302A", text_soft="#344B40",
    text_muted="#5E7267", text_faint="#718479", accent="#087F6B", accent_deep="#087F6B",
    accent_hover="#066A59", accent_ink="#FFFFFF", info="#2563A6", warning="#956009", error="#B83232")
TOKENS = ThemeTokens()

PEACH_LIGHT_TOKENS = ThemeTokens(
    background="#FEF5F9", background_deep="#FBE4EA", surface="#FEF9FC",
    surface_sunken="#FDF0F5", surface_raised="#FDF0F5", surface_hover="#FBE3EC",
    border="#F4CFDE", border_strong="#EFC3D3", text="#321B2D", text_soft="#594152",
    text_muted="#79616F", text_faint="#927585", accent="#B72159", accent_deep="#B84C6F",
    accent_hover="#A93F64", accent_ink="#FFFFFF", progress_fill="#CD6588",
    progress_track="#FCD9E1", secondary_ink="#B72159", secondary_surface="#FEF9FC",
    header_surface="#FEF5F9", banner_surface="#FCE8EE", nav_surface="#FADAE3",
    secondary_border="#DF7899", badge_surface="#FCE3EC",
    info="#85506D", warning="#956009", error="#B83248")
PEACH_DARK_TOKENS = ThemeTokens(
    background="#17181C", background_deep="#17181C", surface="#202126",
    surface_sunken="#292A30", surface_raised="#292A30", surface_hover="#33343B",
    border="#383940", border_strong="#505159", text="#EFECEF", text_soft="#D1CDD2",
    text_muted="#ADA6AE", text_faint="#8E8790", accent="#D38AA1", accent_deep="#9F526E",
    accent_hover="#B36782", accent_ink="#241A20", progress_fill="#C989A0",
    progress_track="#353039", secondary_ink="#EFECEF", secondary_surface="#202126",
    header_surface="#17181C", banner_surface="#202126", nav_surface="#49333E",
    secondary_border="#737079", badge_surface="#3B2D35",
    info="#B7BCCF", warning="#E8C185", error="#FF9FAE")



def select_theme(light: bool, color_theme: str = "classic") -> None:
    from dataclasses import fields
    if color_theme == "peach":
        chosen = PEACH_LIGHT_TOKENS if light else PEACH_DARK_TOKENS
    else:
        chosen = LIGHT_TOKENS if light else DARK_TOKENS
    for field in fields(TOKENS):
        setattr(TOKENS, field.name, getattr(chosen, field.name))


def tint(color: str, alpha: int) -> str:
    return f"rgba({int(color[1:3],16)}, {int(color[3:5],16)}, {int(color[5:7],16)}, {alpha})"


def feedback_style(widget, role: str, *, bold=False) -> None:
    widget.setProperty("colorRole", role)
    widget.setProperty("feedbackBold", bold)
    color = getattr(TOKENS, {"success": "accent"}.get(role, role))
    widget.setStyleSheet(f"color: {color};" + ("font-weight: 600;" if bold else ""))


def desktop_stylesheet(tokens: ThemeTokens = TOKENS) -> str:
    """Return the one app-wide style sheet built from semantic tokens."""

    return f"""
    QWidget {{
        color: {tokens.text};
        font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI";
        font-size: 14px;
    }}
    QMainWindow, QWidget#appRoot, QScrollArea, QScrollArea > QWidget > QWidget {{
        background: {tokens.background};
    }}
    QScrollArea {{ border: 0; }}
    QScrollBar:vertical {{
        background: transparent; width: 10px; margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {tokens.border_strong}; border-radius: 5px; min-height: 32px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QFrame#appHeader {{
        background: {tokens.header_surface or tokens.background_deep};
        border-bottom: 1px solid {tokens.header_surface or tokens.border};
    }}
    QLabel#brandMark {{
        background: {tokens.accent}; color: {tokens.accent_ink};
        border-radius: 11px; font-size: 15px; font-weight: 800;
    }}
    QLabel#appName {{ font-size: 19px; font-weight: 750; color: {tokens.text}; }}
    QLabel#appPurpose, QLabel#muted, QLabel[muted="true"] {{ color: {tokens.text_muted}; }}
    QLabel#appPurpose {{ font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; font-weight: 600; color: {tokens.text_soft}; }}
    QPushButton#navButton {{
        background: transparent; border: 1px solid transparent;
        border-radius: {tokens.radius_small}px; color: {tokens.text_muted};
        padding: 8px 13px; font-weight: 650;
    }}
    QPushButton#navButton:hover {{ background: {tokens.surface}; color: {tokens.text}; }}
    QPushButton#navButton:focus {{ border: 1px solid {tokens.accent}; }}
    QPushButton#navButton[active="true"] {{
        background: {tokens.nav_surface or tokens.surface_raised}; color: {tokens.accent};
        border: 1px solid {tokens.nav_surface or tokens.border_strong};
    }}
    QLabel#pageTitle {{ font-size: 29px; font-weight: 780; color: {tokens.text}; }}
    QLabel#pageIntro {{ font-size: 14px; color: {tokens.text_muted}; }}
    QFrame#surfaceCard, QFrame#providerCard, QFrame#scheduleCard,
    QFrame#overallStatusCard, QFrame#weeklySafetyCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {tokens.surface}, stop:1 {tokens.surface});
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius}px;
    }}
    QFrame#overallStatusCard {{
        background: {tokens.banner_surface or tokens.surface_raised}; border: 1px solid {tokens.banner_surface or tokens.border_strong};
    }}
    QLabel#overallIcon {{
        background: transparent; border: 0;
        font-size: 20px; font-weight: 800;
    }}
    QLabel#overallIcon[tone="success"] {{ color: #FFFFFF; background: {tokens.accent_deep}; border-radius: 16px; }}
    QLabel#overallIcon[tone="info"] {{ color: {tokens.accent}; }}
    QLabel#overallIcon[tone="warning"] {{ color: {tokens.warning}; }}
    QLabel#overallIcon[tone="error"] {{ color: {tokens.error}; }}
    QLabel#overallTitle {{ font-size: 18px; font-weight: 760; color: {tokens.text}; }}
    QLabel#eyebrow {{
        color: {tokens.accent}; font-size: 11px; font-weight: 800;
    }}
    QLabel#sectionTitle {{ font-size: 17px; font-weight: 720; color: {tokens.text}; }}
    QLabel#providerName {{ font-size: 18px; font-weight: 740; color: {tokens.text}; }}
    QLabel#countdown {{ font-size: 29px; font-weight: 780; color: {tokens.text}; }}
    QLabel#weeklyValue {{ font-size: 23px; font-weight: 780; color: {tokens.text}; }}
    QLabel#scheduleMode {{ font-size: 26px; font-weight: 770; color: {tokens.text}; }}
    QLabel#scheduleNext {{ font-size: 17px; font-weight: 700; color: {tokens.accent}; }}
    QLabel#lastAction {{ color: {tokens.text_muted}; font-size: 12px; padding: 0 4px; }}
    QLabel#secondaryMetric {{ color: {tokens.text_soft}; font-size: 13px; }}
    QLabel#detail {{ color: {tokens.text_muted}; line-height: 1.4; }}
    QLabel#statusPill {{
        border-radius: 10px; padding: 4px 9px; font-size: 10px; font-weight: 800;
    }}
    QLabel#statusPill[tone="success"] {{
        color: {tokens.accent}; background: {tokens.badge_surface or tint(tokens.accent, 24)}; border: 1px solid {tokens.badge_surface or tint(tokens.accent, 80)};
    }}
    QLabel#statusPill[tone="warning"] {{
        color: {tokens.warning}; background: {tint(tokens.warning, 20)}; border: 1px solid {tint(tokens.warning, 80)};
    }}
    QLabel#statusPill[tone="error"] {{
        color: {tokens.error}; background: {tint(tokens.error, 20)}; border: 1px solid {tint(tokens.error, 80)};
    }}
    QLabel#statusPill[tone="info"] {{
        color: {tokens.info}; background: {tint(tokens.info, 20)}; border: 1px solid {tint(tokens.info, 80)};
    }}
    QLabel#statusPill[tone="neutral"] {{
        color: {tokens.text_muted}; background: {tokens.surface_sunken};
        border: 1px solid {tokens.border};
    }}
    QCheckBox#automationToggle {{
        spacing: 13px; font-size: 17px; font-weight: 720; color: {tokens.text};
    }}
    QCheckBox::indicator {{
        width: 38px; height: 22px; border-radius: 11px;
        background: {tokens.surface_sunken}; border: 1px solid {tokens.border_strong};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {tokens.text_muted}; }}
    QCheckBox::indicator:checked {{
        background: {tokens.accent}; border: 1px solid {tokens.accent};
    }}
    QCheckBox:focus {{ color: {tokens.accent}; }}
    QRadioButton {{ spacing: 9px; padding: 7px 10px; color: {tokens.text}; }}
    QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 10px;
        border: 1px solid {tokens.border_strong}; background: {tokens.surface}; }}
    QRadioButton::indicator:checked {{ width: 8px; height: 8px; background: {tokens.surface}; border: 6px solid {tokens.accent}; border-radius: 10px; }}
    QRadioButton:checked {{ color: {tokens.accent}; background: {tokens.surface_raised}; border-radius: 8px; }}
    QMenu {{ background: {tokens.surface}; color: {tokens.text}; border: 1px solid {tokens.border}; padding: 5px; }}
    QMenu::item:selected {{ background: {tokens.surface_hover}; color: {tokens.accent}; }}
    QComboBox, QTimeEdit {{
        min-width: 132px; background: {tokens.surface_raised}; color: {tokens.text};
        border: 1px solid {tokens.border_strong}; border-radius: {tokens.radius_small}px;
        padding: 8px 12px;
    }}
    QComboBox:hover, QTimeEdit:hover {{ border-color: {tokens.accent}; }}
    QComboBox:focus, QTimeEdit:focus {{ border: 1px solid {tokens.accent}; }}
    QTimeEdit {{
        min-width: 152px; padding: 8px 38px 8px 12px; font-weight: 680;
        selection-background-color: {tokens.accent_deep};
        selection-color: #F4FFFB;
    }}
    QTimeEdit::up-button, QTimeEdit::down-button {{
        subcontrol-origin: border; width: 28px;
        background: {tokens.surface_sunken};
        border-left: 1px solid {tokens.border_strong};
    }}
    QTimeEdit::up-button {{
        subcontrol-position: top right;
        border-bottom: 1px solid {tokens.border};
        border-top-right-radius: {tokens.radius_small}px;
    }}
    QTimeEdit::down-button {{
        subcontrol-position: bottom right;
        border-bottom-right-radius: {tokens.radius_small}px;
    }}
    QTimeEdit::up-button:hover, QTimeEdit::down-button:hover {{
        background: {tokens.surface_hover};
    }}
    QTimeEdit:focus::up-button, QTimeEdit:focus::down-button {{
        background: {tokens.surface_hover};
        border-left-color: {tokens.accent_deep};
    }}
    QTimeEdit:focus::up-button {{ border-bottom-color: {tokens.accent_deep}; }}
    QTimeEdit::up-button:pressed, QTimeEdit::down-button:pressed {{
        background: {tokens.accent_deep};
    }}
    QComboBox::drop-down {{ border: 0; width: 24px; }}
    QComboBox#languageSelector {{ padding-right: 40px; }}
    QComboBox#languageSelector::drop-down {{ width: 36px; border-left: 1px solid {tokens.border}; }}
    QComboBox#languageSelector::down-arrow {{ image: none; width: 0; height: 0; }}
    QComboBox QAbstractItemView {{
        background: {tokens.surface_raised}; color: {tokens.text};
        border: 1px solid {tokens.border_strong}; selection-background-color: {tokens.accent_deep};
    }}
    QPushButton {{
        background: {tokens.surface_raised}; color: {tokens.text_soft};
        border: 1px solid {tokens.border_strong}; border-radius: {tokens.radius_small}px;
        padding: 9px 14px; font-weight: 650;
    }}
    QPushButton:hover {{ background: {tokens.surface_hover}; color: {tokens.text}; }}
    QPushButton:focus {{ border: 1px solid {tokens.accent}; }}
    QPushButton:disabled {{ color: {tokens.text_faint}; background: {tokens.surface_sunken}; }}
    QPushButton#primaryButton {{
        background: {tokens.accent_deep}; color: #FFFFFF; border: 1px solid {tokens.accent};
    }}
    QPushButton#primaryButton:hover {{ background: {tokens.accent_hover}; }}
    QPushButton#secondaryButton {{
        background: {tokens.secondary_surface or tokens.surface_raised}; border: 1px solid {tokens.secondary_border or tokens.border_strong};
        border-radius: 8px; color: {tokens.secondary_ink or tokens.text}; padding: 8px 14px;
    }}
    QPushButton#secondaryButton:hover {{ border-color: {tokens.accent}; color: {tokens.accent}; }}
    QPushButton#secondaryButton:disabled {{ color: {tokens.text_muted}; border-color: {tokens.border}; }}
    QPushButton#linkButton {{
        background: {tokens.surface_sunken}; color: {tokens.text_soft};
        border: 1px solid {tokens.border}; text-align: left;
    }}
    QPushButton#linkButton:hover {{ color: {tokens.accent}; border-color: {tokens.accent_deep}; }}
    QFrame#settingRow {{
        background: {tokens.surface_sunken}; border: 1px solid {tokens.border};
        border-radius: {tokens.radius_small}px;
    }}
    QFrame#weeklySchedulePanel {{
        background: transparent; border: 0;
    }}
    QFrame#weeklyGroupCard, QFrame#weeklyPreviewCard, QFrame#aboutActions {{
        background: {tokens.surface_raised}; border: 1px solid {tokens.border_strong};
        border-radius: {tokens.radius_small}px;
    }}
    QLabel#weeklyGroupTitle {{
        color: {tokens.text}; font-size: 14px; font-weight: 750;
    }}
    QFrame#weeklyDayRow, QFrame#weeklyPreviewMetric, QFrame#aboutStep {{
        background: {tokens.surface_sunken}; border: 1px solid {tokens.border};
        border-radius: {tokens.radius_small}px;
    }}
    QLabel#weeklyDayLabel {{ color: {tokens.text_soft}; font-weight: 680; }}
    QFrame#weeklyPreviewCard {{ border-left: 3px solid {tokens.accent}; }}
    QLabel#weeklyPreviewLabel {{ color: {tokens.text_muted}; font-size: 12px; }}
    QLabel#weeklyPreviewValue {{ color: {tokens.accent}; font-size: 19px; font-weight: 760; }}
    QFrame#aboutHero {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {tokens.surface}, stop:1 {tokens.surface});
        border: 1px solid {tokens.border_strong}; border-radius: {tokens.radius_large}px;
    }}
    QLabel#aboutProductTitle {{ font-size: 24px; font-weight: 780; color: {tokens.text}; }}
    QLabel#aboutStepNumber {{
        color: {tokens.accent}; background: {tint(tokens.accent, 16)}; border: 1px solid {tint(tokens.accent, 80)};
        border-radius: 14px; font-weight: 800;
    }}
    QLabel#aboutStepTitle {{ color: {tokens.text}; font-weight: 720; }}
    QLabel#diagnosticValue {{
        color: {tokens.text_muted}; font-family: "Cascadia Mono", Consolas;
        font-size: 12px; background: {tokens.surface_sunken};
        border: 1px solid {tokens.border}; border-radius: {tokens.radius_small}px;
        padding: 12px;
    }}
    QLabel#updateState[status="success"] {{ color: {tokens.accent}; }}
    QLabel#updateState[status="error"] {{ color: {tokens.error}; }}
    QLabel#updateState[status="warning"] {{ color: {tokens.warning}; }}
    QFrame#providerCard[tone="success"] {{ border-left: 3px solid {tokens.accent}; }}
    QFrame#providerCard[tone="warning"] {{ border-left: 3px solid {tokens.warning}; }}
    QFrame#providerCard[tone="error"] {{ border-left: 3px solid {tokens.error}; }}
    QFrame#providerCard[tone="info"] {{ border-left: 3px solid {tokens.info}; }}
    QFrame#cardRule {{
        background: {tokens.border}; border: 0; max-height: 1px;
    }}
    QFrame#appHeader QWidget#brandBlock, QFrame#appHeader QWidget#headerControls {{
        background: transparent;
    }}
    QFrame#healthRow {{
        background: {tokens.surface_sunken}; border: 1px solid {tokens.border};
        border-radius: {tokens.radius_small}px;
    }}
    QFrame#healthSummary {{
        background: {tokens.surface_raised}; border: 1px solid {tokens.border_strong};
        border-radius: {tokens.radius_small}px;
    }}
    QLabel#healthLabel {{ font-size: 14px; font-weight: 700; color: {tokens.text}; }}
    QLabel#healthDetail {{ font-size: 12px; color: {tokens.text_muted}; }}
    QPushButton#disclosureToggle {{
        background: transparent; border: 0; color: {tokens.text_muted};
        padding: 4px 2px; font-weight: 650; text-align: left;
    }}
    QPushButton#disclosureToggle:hover {{ color: {tokens.text}; }}
    QPushButton#disclosureToggle:checked {{ color: {tokens.accent}; }}
    QFrame#appFooter {{
        background: {tokens.header_surface or tokens.background_deep};
        border-top: 1px solid {tokens.header_surface or tokens.border};
    }}
    QLabel#footerPromise {{ color: {tokens.text_faint}; font-size: 12px; }}
    QLabel#footerVersion {{ color: {tokens.text_faint}; font-size: 12px; }}
    QLabel#wordmarkPrimary {{ font-size: 27px; font-weight: 800; color: {tokens.text}; }}
    QLabel#wordmarkAccent {{ font-size: 27px; font-weight: 800; color: {tokens.accent}; }}
    QLabel#wordmarkQualifier {{ font-size: 12px; font-weight: 650; color: {tokens.text_muted}; }}
    QLabel#metricLabel {{ color: {tokens.text_soft}; font-size: 12px; font-weight: 650; }}
    QProgressBar#usageBar, QProgressBar#weeklyBar {{
        background: {tokens.progress_track or tokens.surface_sunken}; border: 0; border-radius: 5px;
    }}
    QProgressBar#usageBar::chunk {{ background: {tokens.progress_fill or tokens.accent}; border-radius: 5px; }}
    QProgressBar#weeklyBar::chunk {{ background: {tokens.progress_fill or tokens.accent}; border-radius: 5px; }}
    QLabel#trustChip {{
        color: {tokens.accent}; background: {tokens.surface_sunken};
        border: 1px solid {tokens.accent_deep}; border-radius: {tokens.radius_small}px;
        padding: 6px 11px; font-size: 11px; font-weight: 700;
    }}
    QFrame#assuranceStrip {{
        background: {tokens.surface_sunken}; border: 1px solid {tokens.border};
        border-radius: {tokens.radius}px;
    }}
    QLabel#assuranceTitle {{ font-size: 13px; font-weight: 720; color: {tokens.text}; }}
    QLabel#assuranceBody {{ font-size: 13px; color: {tokens.text_soft}; }}
    QLabel#previewTag {{
        color: {tokens.accent}; background: {tint(tokens.accent, 18)}; border: 1px solid {tint(tokens.accent, 64)};
        border-radius: 9px; padding: 3px 8px; font-size: 10px; font-weight: 800;
    }}
    QToolTip {{
        background: {tokens.surface_raised}; color: {tokens.text};
        border: 1px solid {tokens.border_strong}; padding: 5px;
    }}
    QMessageBox {{ background: {tokens.background}; }}
    """

