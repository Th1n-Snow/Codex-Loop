"""Live appearance and language preferences, independent of warm-up scheduling."""
from PySide6.QtCore import QObject, Qt, Signal, QPointF, QEvent, QTimer
from PySide6.QtGui import QPalette, QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QRadioButton,QButtonGroup,QComboBox
from .ui_theme import TOKENS,select_theme,desktop_stylesheet,feedback_style
from . import zh_cn


def system_is_light():
    app=QApplication.instance()
    if app is not None:
        scheme=app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:return True
        if scheme == Qt.ColorScheme.Dark:return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            return bool(winreg.QueryValueEx(key,'AppsUseLightTheme')[0])
    except (ImportError,OSError):
        return True


class AppearanceManager(QObject):
    def __init__(self, window, settings):
        super().__init__(window)
        self.window=window
        self.mode=settings.theme_mode
        self.color_theme=settings.color_theme
        self.caption_timer=QTimer(self)
        self.caption_timer.setSingleShot(True)
        self.caption_timer.timeout.connect(self.apply_native_caption)
        window.installEventFilter(self)
        zh_cn.install()
        zh_cn.set_language(settings.ui_language,QApplication.instance())
        select_theme(system_is_light() if self.mode=='system' else self.mode=='light', self.color_theme)
        app=QApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._system_changed)

    def _system_changed(self,*_args):
        if self.mode=='system':self.apply_theme(self.mode)
        else:self.caption_timer.start(0)

    def eventFilter(self,watched,event):
        if watched is self.window and event.type() in (
                QEvent.Type.Show,QEvent.Type.WinIdChange,QEvent.Type.ActivationChange,
                QEvent.Type.WindowActivate,QEvent.Type.WindowDeactivate):
            # Let Qt finish its native theme update before restoring our caption.
            self.caption_timer.start(0)
        return super().eventFilter(watched,event)

    def apply_native_caption(self):
        import sys
        app=QApplication.instance()
        if sys.platform!='win32' or app is None or app.platformName()!='windows':return
        try:
            import ctypes
            from ctypes import wintypes
            set_attribute=ctypes.windll.dwmapi.DwmSetWindowAttribute
            set_attribute.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            set_attribute.restype=ctypes.c_long
            handle=int(self.window.winId())
            # Hide only the caption icon. Keep the QIcon for the taskbar/tray
            # and keep the normal system menu and window controls available.
            user32=ctypes.windll.user32
            get_style=getattr(user32,'GetWindowLongPtrW',user32.GetWindowLongW)
            set_style=getattr(user32,'SetWindowLongPtrW',user32.SetWindowLongW)
            get_style.argtypes=[wintypes.HWND,ctypes.c_int]
            get_style.restype=ctypes.c_ssize_t
            set_style.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t]
            set_style.restype=ctypes.c_ssize_t
            extended_style=get_style(handle,-20)
            if not extended_style & 0x00000001:  # WS_EX_DLGMODALFRAME
                set_style(handle,-20,extended_style | 0x00000001)
                refresh=user32.SetWindowPos
                refresh.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
                refresh.restype=wintypes.BOOL
                refresh(handle,None,0,0,0,0,0x0037)  # frame changed, no move/size/activation
            light=system_is_light() if self.mode=='system' else self.mode=='light'
            def set_value(attribute,value):
                data=wintypes.DWORD(value)
                return set_attribute(handle,attribute,ctypes.byref(data),ctypes.sizeof(data))
            def colorref(value):
                c=QColor(value)
                return c.red() | (c.green()<<8) | (c.blue()<<16)
            set_value(20,0 if light else 1)
            # Explicit colors also override the Windows active-title accent color.
            set_value(35,colorref(TOKENS.background_deep))
            set_value(36,colorref(TOKENS.text if self.window.isActiveWindow() else TOKENS.text_muted))
            set_value(34,colorref(TOKENS.border))
        except (OSError,AttributeError):pass

    def apply_theme(self,mode):
        self.mode=mode
        light=system_is_light() if mode=='system' else mode=='light'
        select_theme(light, self.color_theme)
        app=QApplication.instance()
        if app is None:return
        palette=QPalette()
        for role,value in ((QPalette.ColorRole.Window,TOKENS.background),
                           (QPalette.ColorRole.WindowText,TOKENS.text),
                           (QPalette.ColorRole.Base,TOKENS.surface),
                           (QPalette.ColorRole.AlternateBase,TOKENS.surface_raised),
                           (QPalette.ColorRole.Text,TOKENS.text),
                           (QPalette.ColorRole.Button,TOKENS.surface_raised),
                           (QPalette.ColorRole.ButtonText,TOKENS.text),
                           (QPalette.ColorRole.ToolTipBase,TOKENS.surface),
                           (QPalette.ColorRole.ToolTipText,TOKENS.text),
                           (QPalette.ColorRole.Highlight,TOKENS.accent_deep),
                           (QPalette.ColorRole.HighlightedText,'#FFFFFF'),
                           (QPalette.ColorRole.PlaceholderText,TOKENS.text_muted)):
            palette.setColor(role,QColor(value))
        palette.setColor(QPalette.ColorGroup.Disabled,QPalette.ColorRole.Text,QColor(TOKENS.text_faint))
        app.setPalette(palette)
        css=desktop_stylesheet()
        app.setStyleSheet(css)
        self.window.setStyleSheet(css)
        for widget in app.allWidgets():
            role=widget.property('colorRole')
            if role:feedback_style(widget,role,bold=bool(widget.property('feedbackBold')))
            kind=widget.property("dashboardGlyph")
            if kind:
                from .dashboard_art import action_icon
                from PySide6.QtCore import QSize
                widget.setIcon(action_icon(kind))
                widget.setIconSize(QSize(18,18))
            widget.update()
        self.apply_native_caption()
        self.caption_timer.start(0)

    def apply_color_theme(self,color_theme):
        self.color_theme=color_theme
        self.apply_theme(self.mode)

    def apply_language(self,language):
        zh_cn.set_language(language,QApplication.instance())
        self.window.refresh_clock()
        panel=getattr(self.window,"update_panel",None)
        if panel is not None:panel.refresh_localized_release_notes()
        for card in self.window.provider_cards.values():card.fit_wrapped_text()
        self.window.schedule_card.fit_wrapped_text()
        self.window.presentation_changed.emit()


class LanguageComboBox(QComboBox):
    """Draw an explicit chevron; native arrows can disappear under Qt stylesheets."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('languageSelector')
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen=QPen(QColor(TOKENS.text_soft),2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        x,y=self.width()-20,self.height()/2
        painter.drawPolyline([QPointF(x-5,y-2),QPointF(x,y+3),QPointF(x+5,y-2)])
        painter.end()


class AppearancePanel(QFrame):
    theme_selected=Signal(str)
    color_theme_selected=Signal(str)
    language_selected=Signal(str)
    def __init__(self,settings,parent=None):
        super().__init__(parent)
        self.setObjectName('surfaceCard')
        layout=QVBoxLayout(self);layout.setContentsMargins(20,16,20,16);layout.setSpacing(10)
        title=QLabel('Appearance and language');title.setObjectName('sectionTitle');layout.addWidget(title)
        row=QHBoxLayout();row.setSpacing(8)
        row.addWidget(QLabel('Color scheme'))
        self.group=QButtonGroup(self);self.theme_buttons={}
        for index,(key,text) in enumerate((('system','System'),('light','Light'),('dark','Dark'))):
            button=QRadioButton(text);button.setAccessibleName(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(button,index);self.theme_buttons[key]=button
            button.setChecked(settings.theme_mode==key)
            button.clicked.connect(lambda checked=False,value=key:self.theme_selected.emit(value) if checked else None)
            row.addWidget(button)
        row.addStretch();layout.addLayout(row)
        colors=QHBoxLayout();colors.addWidget(QLabel('Theme color'))
        self.color_group=QButtonGroup(self);self.color_buttons={}
        for key,text in (('classic','Classic mint'),('peach','Peach blossom')):
            button=QRadioButton(text);button.setAccessibleName(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.color_group.addButton(button);self.color_buttons[key]=button
            button.setChecked(settings.color_theme==key)
            button.clicked.connect(lambda checked=False,value=key:self.color_theme_selected.emit(value) if checked else None)
            colors.addWidget(button)
        colors.addStretch();layout.addLayout(colors)
        lang=QHBoxLayout();lang.addWidget(QLabel('Language'))
        self.language_combo=LanguageComboBox();self.language_combo.setAccessibleName('Language')
        self.language_combo.addItem('简体中文','zh_CN');self.language_combo.addItem('English','en')
        self.language_combo.setCurrentIndex(self.language_combo.findData(settings.ui_language))
        self.language_combo.currentIndexChanged.connect(lambda _index:self.language_selected.emit(self.language_combo.currentData()))
        lang.addWidget(self.language_combo);lang.addStretch();layout.addLayout(lang)
        hint=QLabel('Changes apply immediately and are saved on this computer.');hint.setProperty('muted',True);hint.setWordWrap(True);layout.addWidget(hint)
        self.feedback=QLabel('');self.feedback.setWordWrap(True);layout.addWidget(self.feedback)

    def restore(self,settings):
        for key,button in self.color_buttons.items():
            blocked=button.blockSignals(True);button.setChecked(key==settings.color_theme);button.blockSignals(blocked)
        for key,button in self.theme_buttons.items():
            blocked=button.blockSignals(True);button.setChecked(key==settings.theme_mode);button.blockSignals(blocked)
        blocked=self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(self.language_combo.findData(settings.ui_language))
        self.language_combo.blockSignals(blocked)

    def saved(self):
        feedback_style(self.feedback,'success');self.feedback.setText('Saved')

    def failed(self,settings):
        self.restore(settings);feedback_style(self.feedback,'error')
        self.feedback.setText('Could not save the setting. Your previous selection has been restored.')
