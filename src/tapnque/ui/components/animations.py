"""
Animated Visual Components for TapNQue Kiosk and Displays.
"""

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


class AnimatedSpinner(QWidget):
    """Rotating circular loader used by the startup splash."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(16)
        self.setFixedSize(66, 66)

    def _advance(self):
        self.angle = (self.angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(8, 8, self.width() - 16, self.height() - 16)

        painter.setPen(QPen(QColor(7, 53, 42, 185), 4))
        painter.drawEllipse(rect)

        painter.setPen(QPen(QColor("#0b9b4a"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, int(-self.angle * 16), -110 * 16)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0b9b4a"))
        painter.drawEllipse(QRectF(self.width() / 2 - 4, self.height() / 2 - 4, 8, 8))


class AnimatedLoadingBar(QWidget):
    """Subtle moving glowing bar animation for splash screens and footers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.offset = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(24)
        self.setFixedHeight(14)

    def sizeHint(self):
        return QSize(560, 14)

    def _advance(self):
        self.offset = (self.offset + 0.012) % 1.2
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        line_y = self.height() / 2
        line_start = 0
        line_end = self.width()

        painter.setPen(QPen(QColor(34, 48, 67, 190), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(line_start, int(line_y), line_end, int(line_y))

        segment_width = max(110, int(self.width() * 0.22))
        span = self.width() + segment_width
        segment_x = int((self.offset * span) - segment_width)

        gradient = QLinearGradient(segment_x, 0, segment_x + segment_width, 0)
        gradient.setColorAt(0.0, QColor(11, 155, 74, 0))
        gradient.setColorAt(0.5, QColor(11, 155, 74, 255))
        gradient.setColorAt(1.0, QColor(11, 155, 74, 0))

        painter.setPen(QPen(gradient, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(segment_x, int(line_y), segment_x + segment_width, int(line_y))


class WaitingSignalAnimation(QWidget):
    """Pulsing equalizer bars for the post-ticket waiting screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(80)
        self.setFixedSize(170, 72)

    def _advance(self):
        self.phase = (self.phase + 1) % 24
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        bar_width = 18
        gap = 10
        base_y = self.height() - 8
        heights = [20, 40, 56, 34, 48, 28]

        for index, base_height in enumerate(heights):
            wave = ((self.phase + index * 3) % 12) / 11.0
            height = int(18 + (base_height * (0.45 + wave * 0.55)))
            x = index * (bar_width + gap)
            y = base_y - height

            gradient = QLinearGradient(x, y, x, base_y)
            gradient.setColorAt(0.0, QColor("#4dd38a"))
            gradient.setColorAt(1.0, QColor("#0a8c3c"))

            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(x, y, bar_width, height, 9, 9)
