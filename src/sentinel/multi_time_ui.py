"""Dashboard editor for an explicit daily list of warm-up appointments."""
from PySide6.QtCore import QTime, QTimer, Signal
from PySide6.QtWidgets import QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QMessageBox
from .ui_components import TimeEntry
from .ui_theme import feedback_style
from .schedule import MULTI,normalize_multi_times,multi_schedule_summary
from datetime import datetime

class MultiTimePanel(QFrame):
    saved = Signal(object)
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setObjectName('surfaceCard')
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,16,20,16)
        layout.setSpacing(10)
        header=QHBoxLayout()
        title=QLabel('每天多个时间')
        title.setObjectName('sectionTitle')
        header.addWidget(title)
        header.addStretch()
        self.mode_label=QLabel()
        self.mode_label.setProperty('muted',True)
        header.addWidget(self.mode_label)
        layout.addLayout(header)
        note=QLabel('每天按设定时间执行预热检查；电脑休眠时错过的时间点不会集中补发。')
        note.setProperty('muted',True)
        note.setWordWrap(True)
        layout.addWidget(note)
        self.grid=QGridLayout()
        self.grid.setSpacing(8)
        layout.addLayout(self.grid)
        self.editors=[]
        self.dirty=False
        actions=QHBoxLayout()
        self.add_button=QPushButton('＋ 添加时间')
        self.add_button.setObjectName('secondaryButton')
        self.add_button.clicked.connect(self.add_time)
        actions.addWidget(self.add_button)
        actions.addStretch()
        self.save_button=QPushButton('保存并使用这些时间')
        self.save_button.setObjectName('primaryButton')
        self.save_button.clicked.connect(self.save)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)
        self.save_feedback=QLabel("")
        self.save_feedback.setObjectName("multiSaveFeedback")
        self.save_feedback.setWordWrap(True)
        self.save_feedback.setMinimumHeight(22)
        layout.addWidget(self.save_feedback)
        self.feedback_timer=QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self._clear_feedback)
        self.status=QLabel()
        self.status.setProperty('muted',True)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.set_times(settings.multi_start_times)
        self.update_status(settings,datetime.now().timestamp())

    def values(self):
        return [(editor.time().hour(),editor.time().minute()) for editor in self.editors]

    def set_times(self,values, *, reset_baseline=True):
        if reset_baseline:
            self._saved_values=normalize_multi_times(values)
        while self.grid.count():
            item=self.grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.editors=[]
        self.dirty=False
        for index,(hour,minute) in enumerate(values):
            row=QFrame()
            line=QHBoxLayout(row)
            line.setContentsMargins(0,0,0,0)
            editor=TimeEntry(QTime(hour,minute))
            editor.setAccessibleName(f'预热时间 {index+1}')
            editor.setMinimumWidth(110)
            editor.timeChanged.connect(self.mark_dirty)
            line.addWidget(editor,1)
            remove=QPushButton('删除')
            remove.setObjectName('secondaryButton')
            remove.setAccessibleName(f'删除预热时间 {index+1}')
            remove.clicked.connect(lambda checked=False,i=index:self.remove_time(i))
            line.addWidget(remove)
            self.editors.append(editor)
            self.grid.addWidget(row,index//2,index%2)
        self.add_button.setEnabled(len(values)<24)

    def add_time(self):
        values=self.values()
        if len(values)>=24:return
        used=set(values)
        value=next(((hour,0) for hour in range(24) if (hour,0) not in used),(12,0))
        self.set_times([*values,value],reset_baseline=False)
        self.mark_dirty()

    def remove_time(self,index):
        values=self.values()
        if 0<=index<len(values):
            values.pop(index)
            self.set_times(values,reset_baseline=False)
            self.mark_dirty()

    def mark_dirty(self, *_args):
        self.dirty=normalize_multi_times(self.values()) != self._saved_values
        self.feedback_timer.stop()
        self.save_button.setText("保存并使用这些时间")
        if not self.dirty:
            self.save_feedback.clear()
            self.update_status(self._settings,datetime.now().timestamp())
            return
        feedback_style(self.save_feedback, "warning")
        self.save_feedback.setText("有未保存的修改，点击保存后才会应用。")
        self.mode_label.setText("有未保存的修改")

    def show_save_success(self, settings):
        self._saved_values=normalize_multi_times(settings.multi_start_times)
        self.dirty=False
        self.save_button.setText("✓ 已保存")
        feedback_style(self.save_feedback, "success", bold=True)
        if not settings.automation_enabled:
            text="✓ 保存成功。自动预热尚未开启，打开开关后生效。"
        elif settings.pause_active(datetime.now().timestamp()):
            text="✓ 保存成功，已选用此时间表；自动预热目前暂停中。"
        else:
            text="✓ 保存成功，时间表已生效。"
        self.save_feedback.setText(text)
        self.feedback_timer.start(6000)

    def show_save_error(self, text):
        self.feedback_timer.stop()
        self.save_button.setText("保存并使用这些时间")
        feedback_style(self.save_feedback, "error")
        self.save_feedback.setText("保存失败："+text)

    def _clear_feedback(self):
        self.save_button.setText("保存并使用这些时间")
        if not self.dirty:self.save_feedback.clear()

    def save(self):
        values=normalize_multi_times(self.values())
        if not values:
            QMessageBox.information(self,'添加预热时间','请至少添加一个时间；要停止自动预热，可关闭仪表盘上的自动预热开关。')
            return
        self.saved.emit(values)

    def update_status(self,settings,now):
        self._settings=settings
        selected=settings.schedule_mode==MULTI
        self.mode_label.setText('有未保存的修改' if self.dirty else
                                '正在使用此计划' if selected else '尚未选用此计划')
        if not selected:
            self.status.setText('编辑时间后，点击“保存并使用这些时间”切换到此计划。')
            return
        summary=multi_schedule_summary(now,settings.multi_start_times,settings.multi_last_slot)
        if not settings.automation_enabled:
            next_text='自动预热已关闭，时间表已保存。'
        elif settings.pause_active(now):
            next_text='计划已暂停，恢复后继续按时间表运行。'
        elif summary.due:
            next_text='已到设定时间，正在等待检查。'
        elif summary.next_action_at is not None:
            target=datetime.fromtimestamp(summary.next_action_at)
            day='今天' if target.date()==datetime.fromtimestamp(now).date() else '明天'
            next_text=f'下次定时检查：{day} {target:%H:%M}'
        else:next_text='请添加预热时间。'
        if settings.multi_last_slot is not None:
            at=datetime.fromtimestamp(settings.multi_last_slot)
            next_text+=f'　上次计划：{at:%m-%d %H:%M} · {settings.multi_last_status}'
        self.status.setText(next_text)
