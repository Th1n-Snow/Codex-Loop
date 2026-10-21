"""Small theme-aware vector marks for dashboard controls."""
from PySide6.QtCore import Qt,QRectF,QSize,QPointF
from PySide6.QtGui import QColor,QPainter,QPen,QPixmap,QIcon,QPolygonF
from PySide6.QtWidgets import QWidget
from .ui_theme import TOKENS

class LoopMark(QWidget):
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Two rounded arcs keep the loop readable; the small orbit dot must
        # stay separate from both ends instead of merging into a C shape.
        side=min(self.width(),self.height())
        p.translate((self.width()-side)/2,(self.height()-side)/2)
        p.scale(side/48,side/48)
        pen=QPen(QColor(TOKENS.accent),7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush)
        ring=QRectF(6,6,36,36)
        p.drawArc(ring,62*16,143*16)
        p.drawArc(ring,235*16,145*16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(TOKENS.progress_fill or TOKENS.accent))
        # 41 degrees on an 18px radius: a distinct dot in the upper-right gap.
        p.drawEllipse(QPointF(37.585,12.191),2.4,2.4)

def action_icon(kind):
    pix=QPixmap(40,40);pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(2,2)
    pen=QPen(QColor(TOKENS.secondary_ink or TOKENS.accent),1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen);p.setBrush(Qt.BrushStyle.NoBrush)
    if kind=='play':p.drawPolygon(QPolygonF([QPointF(5,3),QPointF(16,10),QPointF(5,17)]))
    elif kind=='history':
        for y in (4,10,16):
            p.drawPoint(QPointF(3,y));p.drawLine(QPointF(7,y),QPointF(17,y))
    else:
        p.drawArc(QRectF(4,4,12,12),30*16,135*16)
        p.drawArc(QRectF(4,4,12,12),210*16,135*16)
        p.drawPolyline(QPolygonF([QPointF(12,3),QPointF(16,4),QPointF(16,8)]))
        p.drawPolyline(QPolygonF([QPointF(8,17),QPointF(4,16),QPointF(4,12)]))
    p.end();pix.setDevicePixelRatio(2)
    return QIcon(pix)
