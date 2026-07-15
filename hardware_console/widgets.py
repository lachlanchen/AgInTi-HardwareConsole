from __future__ import annotations

import math
import re
from typing import Sequence

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


INK = QColor("#17212B")
MUTED = QColor("#687482")
GRID = QColor("#DDE4E8")
TEAL = QColor("#22B8A7")
AMBER = QColor("#E6A23C")
BLUE = QColor("#55A7FF")
RED = QColor("#E35D6A")
PAPER = QColor("#F7F5EF")


class StatusPill(QLabel):
    def __init__(self, text: str = "Offline") -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(82)
        self.set_online(False)

    def set_online(self, online: bool, text: str | None = None) -> None:
        color = "#168878" if online else "#9A5660"
        background = "#DDF6F1" if online else "#F8E4E7"
        self.setText(text or ("Online" if online else "Offline"))
        self.setStyleSheet(
            f"color:{color}; background:{background}; border-radius:11px; "
            "padding:4px 10px; font-weight:700; font-size:11px;"
        )


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "--", unit: str = "") -> None:
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(3)
        title_label = QLabel(title.upper())
        title_label.setObjectName("metricTitle")
        layout.addWidget(title_label)
        row = QHBoxLayout()
        row.setSpacing(5)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.unit_label = QLabel(unit)
        self.unit_label.setObjectName("metricUnit")
        row.addWidget(self.value_label)
        row.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch()
        layout.addLayout(row)

    def set_value(self, value: str | int | float, unit: str | None = None) -> None:
        self.value_label.setText(str(value))
        if unit is not None:
            self.unit_label.setText(unit)


class HistoryPlot(QWidget):
    def __init__(self, title: str, names: tuple[str, str]) -> None:
        super().__init__()
        self.title = title
        self.names = names
        self.series: list[list[float]] = [[], []]
        self.setMinimumHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def append(self, first: float, second: float) -> None:
        self.series[0].append(float(first))
        self.series[1].append(float(second))
        self.series[0] = self.series[0][-180:]
        self.series[1] = self.series[1][-180:]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(rect, 16, 16)

        plot = rect.adjusted(48, 42, -18, -30)
        painter.setPen(QPen(GRID, 1))
        for index in range(5):
            y = plot.top() + plot.height() * index / 4
            painter.drawLine(plot.left(), y, plot.right(), y)

        all_values = self.series[0] + self.series[1]
        maximum = max(all_values, default=1.0)
        minimum = min(all_values, default=0.0)
        if math.isclose(maximum, minimum):
            maximum = minimum + 1.0

        painter.setPen(INK)
        painter.setFont(QFont("Bahnschrift", 11, QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect.left() + 16, rect.top() + 10, 250, 24), self.title)
        painter.setFont(QFont("Cascadia Mono", 8))
        painter.setPen(MUTED)
        painter.drawText(8, int(plot.top() + 4), f"{maximum:.0f}")
        painter.drawText(8, int(plot.bottom()), f"{minimum:.0f}")

        for data, color in zip(self.series, (TEAL, AMBER)):
            if len(data) < 2:
                continue
            path = QPainterPath()
            for index, value in enumerate(data):
                x = plot.left() + plot.width() * index / max(1, len(data) - 1)
                y = plot.bottom() - plot.height() * (value - minimum) / (maximum - minimum)
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.setPen(QPen(color, 2.2))
            painter.drawPath(path)

        legend_x = plot.right() - 180
        for index, (name, color) in enumerate(zip(self.names, (TEAL, AMBER))):
            x = legend_x + index * 92
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(x, rect.top() + 17, 7, 7))
            painter.setPen(MUTED)
            painter.setFont(QFont("Aptos", 8))
            painter.drawText(QRectF(x + 11, rect.top() + 11, 78, 18), name)


class SpectrumPlot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.values = [0.0] * 18
        self.mode = "Auto"
        self.setMinimumHeight(330)

    def set_values(self, values: Sequence[float]) -> None:
        incoming = [float(value) for value in values[:18]]
        self.values = incoming + [0.0] * (18 - len(incoming))
        self.update()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(outer, 18, 18)
        plot = outer.adjusted(58, 48, -24, -46)

        values = list(self.values)
        raw_max = max(values, default=1.0)
        if self.mode == "Normalize" and raw_max > 0:
            values = [value / raw_max for value in values]
            maximum = 1.0
        elif self.mode == "Fixed 16-bit":
            maximum = 65535.0
        else:
            maximum = max(raw_max * 1.08, 1.0)

        painter.setPen(QPen(GRID, 1))
        for index in range(5):
            y = plot.bottom() - plot.height() * index / 4
            painter.drawLine(plot.left(), y, plot.right(), y)
            painter.setPen(MUTED)
            painter.setFont(QFont("Cascadia Mono", 8))
            label = maximum * index / 4
            painter.drawText(QRectF(5, y - 8, 48, 16), Qt.AlignmentFlag.AlignRight, f"{label:.0f}")
            painter.setPen(QPen(GRID, 1))

        painter.setPen(INK)
        painter.setFont(QFont("Bahnschrift", 12, QFont.Weight.DemiBold))
        painter.drawText(QRectF(18, 12, 360, 26), "AS7343 · 18-channel live vector")

        slot = plot.width() / 18
        points = QPainterPath()
        for index, value in enumerate(values):
            x = plot.left() + slot * (index + 0.5)
            y = plot.bottom() - plot.height() * min(max(value / maximum, 0.0), 1.0)
            bar = QRectF(x - slot * 0.27, y, slot * 0.54, plot.bottom() - y)
            hue = 190 - 145 * index / 17
            color = QColor.fromHsvF(hue / 360.0, 0.58, 0.86)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar, 3, 3)
            if index == 0:
                points.moveTo(x, y)
            else:
                points.lineTo(x, y)
            painter.setPen(MUTED)
            painter.setFont(QFont("Cascadia Mono", 7))
            painter.drawText(
                QRectF(x - slot / 2, plot.bottom() + 7, slot, 16),
                Qt.AlignmentFlag.AlignCenter,
                str(index),
            )
        painter.setPen(QPen(INK, 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(points)


class PinMapWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.mode = "H7 lamp + sensors"
        self.setMinimumSize(820, 520)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F6F3EB"))
        if self.mode.startswith("H7"):
            self._draw_h7(painter)
        elif self.mode.startswith("F103"):
            self._draw_f103(painter)
        else:
            self._draw_esp32(painter)

    def _board(self, painter: QPainter, rect: QRectF, color: QColor) -> None:
        painter.setPen(QPen(color.darker(145), 2))
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 22, 22)
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1))
        for offset in range(18, int(rect.width()), 28):
            painter.drawLine(rect.left() + offset, rect.top() + 12, rect.left() + offset, rect.bottom() - 12)

    def _pin(self, painter: QPainter, x: float, y: float, label: str, color: QColor, right: bool = False) -> None:
        painter.setBrush(color)
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.drawEllipse(QRectF(x - 6, y - 6, 12, 12))
        painter.setPen(INK)
        painter.setFont(QFont("Cascadia Mono", 9, QFont.Weight.DemiBold))
        box = QRectF(x + 12 if right else x - 126, y - 10, 114, 20)
        align = Qt.AlignmentFlag.AlignLeft if right else Qt.AlignmentFlag.AlignRight
        painter.drawText(box, align | Qt.AlignmentFlag.AlignVCenter, label)

    def _trace(self, painter: QPainter, start, end, color: QColor, label: str) -> None:
        path = QPainterPath()
        path.moveTo(*start)
        middle_x = start[0] + (end[0] - start[0]) * 0.55
        path.cubicTo(middle_x, start[1], middle_x, end[1], end[0], end[1])
        painter.setPen(QPen(color, 3))
        painter.drawPath(path)
        painter.setPen(color.darker(130))
        painter.setFont(QFont("Aptos", 9, QFont.Weight.DemiBold))
        painter.drawText(QRectF(middle_x - 60, (start[1] + end[1]) / 2 - 18, 120, 18), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_h7(self, painter: QPainter) -> None:
        board = QRectF(250, 42, 300, 430)
        self._board(painter, board, QColor("#1E2F38"))
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Bahnschrift", 17, QFont.Weight.Bold))
        painter.drawText(QRectF(300, 72, 200, 32), Qt.AlignmentFlag.AlignCenter, "STM32H743")
        painter.setFont(QFont("Aptos", 10))
        painter.setPen(QColor("#AFC5CC"))
        painter.drawText(QRectF(300, 105, 200, 22), Qt.AlignmentFlag.AlignCenter, "sensor head · LCD")

        pins = {
            "PB8 · SCL": (250, 165, TEAL, False),
            "PB9 · SDA": (550, 195, TEAL, True),
            "PA0 · PWM 1": (250, 255, AMBER, False),
            "PA1 · PWM 2": (550, 345, AMBER, True),
            "3V3": (250, 390, BLUE, False),
            "GND": (550, 420, RED, True),
        }
        for label, (x, y, color, right) in pins.items():
            self._pin(painter, x, y, label, color, right)

        monitor = QRectF(620, 108, 160, 152)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(TEAL, 2))
        painter.drawRoundedRect(monitor, 16, 16)
        painter.setPen(INK)
        painter.setFont(QFont("Bahnschrift", 12, QFont.Weight.Bold))
        painter.drawText(QRectF(632, 120, 136, 24), Qt.AlignmentFlag.AlignCenter, "I2C BUS")
        painter.setFont(QFont("Cascadia Mono", 8))
        painter.drawText(QRectF(640, 153, 120, 90), "AS7343   0x39\nTSL2591   0x29\nINA219-1  0x41\nINA219-2  0x40")

        mos = QRectF(620, 310, 160, 118)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(AMBER, 2))
        painter.drawRoundedRect(mos, 16, 16)
        painter.setPen(INK)
        painter.setFont(QFont("Bahnschrift", 12, QFont.Weight.Bold))
        painter.drawText(QRectF(632, 323, 136, 24), Qt.AlignmentFlag.AlignCenter, "MOS PWM ×2")
        painter.setFont(QFont("Aptos", 9))
        painter.drawText(QRectF(638, 356, 124, 58), "External lamp power\nPWM ≤ 500 Hz\nShared ground")

        self._trace(painter, (550, 180), (620, 170), TEAL, "SDA / SCL")
        self._trace(painter, (550, 300), (620, 365), AMBER, "TIM2")

    def _draw_f103(self, painter: QPainter) -> None:
        board = QRectF(250, 95, 300, 340)
        self._board(painter, board, QColor("#26393A"))
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Bahnschrift", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(290, 125, 220, 34), Qt.AlignmentFlag.AlignCenter, "STM32F103")
        self._pin(painter, 250, 235, "PA0 / A0 · DATA", AMBER, False)
        self._pin(painter, 550, 185, "3V3", BLUE, True)
        self._pin(painter, 550, 270, "SWIO", TEAL, True)
        self._pin(painter, 550, 310, "SWCLK", TEAL, True)
        self._pin(painter, 550, 385, "GND", RED, True)

        led1 = QRectF(650, 150, 110, 110)
        led2 = QRectF(650, 330, 110, 110)
        for rect, title in ((led1, "PIXEL 1"), (led2, "PIXEL 2")):
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(QPen(AMBER, 2))
            painter.drawRoundedRect(rect, 18, 18)
            painter.setPen(INK)
            painter.setFont(QFont("Bahnschrift", 11, QFont.Weight.Bold))
            painter.drawText(rect.adjusted(6, 10, -6, -70), Qt.AlignmentFlag.AlignCenter, title)
            painter.setFont(QFont("Cascadia Mono", 8))
            painter.drawText(rect.adjusted(10, 42, -10, -8), Qt.AlignmentFlag.AlignCenter, "VCC  GND\nDIN  DOUT")
        self._trace(painter, (250, 235), (650, 205), AMBER, "330 Ω")
        self._trace(painter, (705, 260), (705, 330), TEAL, "DOUT → DIN")

    def _draw_esp32(self, painter: QPainter) -> None:
        board = QRectF(270, 42, 260, 430)
        self._board(painter, board, QColor("#202A32"))
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Bahnschrift", 17, QFont.Weight.Bold))
        painter.drawText(QRectF(290, 72, 220, 34), Qt.AlignmentFlag.AlignCenter, "ESP32-S3 N8R8")
        self._pin(painter, 530, 160, "3V3", BLUE, True)
        self._pin(painter, 530, 235, "IO9 · SCL", TEAL, True)
        self._pin(painter, 270, 285, "IO8 · SDA", TEAL, False)
        self._pin(painter, 270, 415, "GND", RED, False)
        sensor = QRectF(620, 175, 160, 160)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(BLUE, 2))
        painter.drawRoundedRect(sensor, 18, 18)
        painter.setPen(INK)
        painter.setFont(QFont("Bahnschrift", 13, QFont.Weight.Bold))
        painter.drawText(QRectF(635, 194, 130, 25), Qt.AlignmentFlag.AlignCenter, "TSL2591")
        painter.setFont(QFont("Cascadia Mono", 9))
        painter.drawText(QRectF(645, 235, 110, 74), "VCC  3V3\nGND  GND\nSCL  IO9\nSDA  IO8")
        self._trace(painter, (530, 235), (620, 255), TEAL, "I2C")


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.line_number_area_paint_event(event)


class FirmwareHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        keyword = QTextCharFormat()
        keyword.setForeground(QColor("#D28A28"))
        keyword.setFontWeight(QFont.Weight.DemiBold)
        comment = QTextCharFormat()
        comment.setForeground(QColor("#70868A"))
        string = QTextCharFormat()
        string.setForeground(QColor("#168878"))
        number = QTextCharFormat()
        number.setForeground(QColor("#4C86C6"))
        self.rules = [
            (re.compile(r"\b(?:if|else|for|while|return|static|const|void|int|uint\w*|bool|class|def|import|from|try|except)\b"), keyword),
            (re.compile(r"//.*$|#.*$"), comment),
            (re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''), string),
            (re.compile(r"\b(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)\b"), number),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, text_format in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), text_format)


class CodeEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.setFont(QFont("Cascadia Mono", 10))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.highlighter = FirmwareHighlighter(self.document())
        self.update_line_number_area_width()
        self.highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 15 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        content = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(content.left(), content.top(), self.line_number_area_width(), content.height())
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#E9ECEB"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#879198"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#FFF5D9"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
