from __future__ import annotations

import html
import json
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsObject,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


COLORS = {
    "gpio": QColor("#DCE7E8"),
    "analog": QColor("#9DD9CF"),
    "bus": QColor("#75C9BC"),
    "pwm": QColor("#F2C166"),
    "debug": QColor("#8FB5D9"),
    "power": QColor("#E99752"),
    "ground": QColor("#6C7A82"),
    "reserved": QColor("#D65A68"),
    "reset": QColor("#C8A4D4"),
}
INK = QColor("#17212B")
PAPER = QColor("#F6F3EB")


def _canonical(pin: dict) -> str:
    return str(pin.get("pin", "")).upper().replace("GPIO", "IO").split("/")[0].strip()


def _describe(device_id: str, raw: dict) -> dict:
    pin = dict(raw)
    name = str(pin.get("pin", "unknown"))
    role = str(pin.get("role", "GPIO"))
    mode = str(pin.get("mode", "unassigned"))
    upper = f"{name} {role} {mode}".upper()
    category = "gpio"
    purpose = "3.3 V digital logic pin. Firmware can use it as input, output, or a supported alternate peripheral function."
    usage = "Confirm the pin's alternate-function table, then configure direction, pull resistor, speed, and output type in firmware."
    electronics = "A GPIO carries a logic signal, not load power. Logic HIGH is near 3.3 V and LOW is near GND. Drive lamps, motors, and relays through a suitable driver."
    caution = "Do not apply a voltage above the MCU rail or draw substantial current directly from this pin."
    group = "gpio"

    if "GND" in upper or "VSS" in upper:
        category, group = "ground", "ground"
        purpose = "Ground: the common 0 V reference and return path for signals and power."
        usage = "Connect controller ground to every externally powered sensor or driver ground before exchanging logic signals."
        electronics = "Voltage is always measured between two points. Without a shared reference, a 3.3 V signal has no reliable meaning to the receiving circuit."
        caution = "Ground is not a current-limiting component. Keep high-current lamp returns away from sensitive sensor traces when possible."
    elif any(token in upper for token in ("3V3", "5V", "VBUS", "VDD", "VBAT", "VDDA")):
        category, group = "power", "power"
        purpose = "Power rail or supply-reference pin."
        usage = "Use only at the labeled voltage and verify whether the board treats it as an input, output, or both before connecting another supply."
        electronics = "Parallel loads share voltage and add current. A regulator must supply the sum of all loads with thermal margin."
        caution = "Never short a power rail to GND, and never join two independently powered rails unless their power-path design explicitly permits it."
    elif any(token in upper for token in ("NC", "RESERVED", "PSRAM", "QSPI")):
        category, group = "reserved", "reserved"
        purpose = "Reserved, internally occupied, or intentionally unconnected pin."
        usage = "Leave this pin unused unless the board schematic and firmware design explicitly release it."
        electronics = "A visible header pad is not proof that the module makes the signal electrically available. Internal memory can consume an apparent GPIO."
        caution = "Using a reserved memory pin can crash the MCU or corrupt execution."
    elif any(token in upper for token in ("SDA", "SCL", "I2C")):
        category, group = "bus", "i2c"
        purpose = "I²C bus line shared by addressed sensors. SDA carries data and SCL carries the clock."
        usage = "Connect every SDA together and every SCL together, with a common GND. Devices on one bus must have unique addresses."
        electronics = "I²C uses open-drain outputs: devices pull the line LOW and pull-up resistors return it HIGH. Excess pull-up strength or wiring capacitance distorts edges."
        caution = "Use 3.3 V pull-ups for these boards. Do not connect a 5 V-pulled I²C module directly."
    elif any(token in upper for token in ("PWM", "TIM2", "LEDC")):
        category, group = "pwm", "pwm"
        purpose = "Timer/PWM signal used to command a MOSFET or dimming input."
        usage = "Connect to the driver's PWM input and share GND. The external supply powers the lamp; this pin only provides the command waveform."
        electronics = "PWM changes average delivered energy through duty cycle while the pin itself switches between logic LOW and HIGH."
        caution = "Check the driver's accepted logic level and maximum PWM frequency. Never power a lamp directly from this pin."
    elif any(token in upper for token in ("ADC", "TOUCH", "ANALOG")):
        category, group = "analog", "analog"
        purpose = "Analog-capable input for measuring a voltage, with optional capacitive-touch capability where listed."
        usage = "Keep the input between GND and the ADC reference; use a divider and protection when measuring a larger voltage."
        electronics = "An ADC converts voltage into a number. Source impedance and sampling time affect accuracy."
        caution = "An ADC input does not safely accept arbitrary external voltage and is not an ammeter."
    elif any(token in upper for token in ("SWD", "JTAG", "SWIO", "SWCLK")):
        category, group = "debug", "debug"
        purpose = "Programming and hardware-debug interface."
        usage = "Connect signal-to-signal plus GND and target voltage reference. Keep these pins available when recovery/debugging is required."
        electronics = "The debugger clocks commands into the MCU and can inspect memory without using the application serial protocol."
        caution = "Reassigning debug pins can make firmware debugging unavailable until reset or boot recovery."
    elif any(token in upper for token in ("UART", "TXD", "RXD", "USART", "USB")):
        category, group = "bus", "serial"
        purpose = "Serial communication signal. TX transmits, RX receives; USB D+/D− form a differential pair."
        usage = "Cross UART TX→RX and RX←TX, and share GND. Keep USB D+/D− paired and avoid attaching unrelated loads while USB is active."
        electronics = "UART is single-ended asynchronous logic; USB uses a timing-sensitive differential pair. They are not interchangeable."
        caution = "These are 3.3 V logic signals, not RS-232 voltage levels."
    elif any(token in upper for token in ("RST", "NRST", "CHIP_PU", "RESET", "EN")):
        category, group = "reset", "reset"
        purpose = "Reset or chip-enable input. Pulling it to its active level restarts or disables the MCU."
        usage = "Normally leave it in the board's default state; use a momentary button or open-drain controller when remote reset is needed."
        electronics = "Reset forces hardware into a known startup state before firmware begins."
        caution = "Noise or a weak supply on this pin causes repeated rebooting that can look like random flashing."

    canonical = _canonical(pin)
    if device_id == "h7":
        if canonical == "PA0":
            category, group = "pwm", "lamp"
            purpose = "TIM2_CH1, currently assigned to MOS PWM input for lamp 1."
        elif canonical == "PA1":
            category, group = "pwm", "lamp"
            purpose = "TIM2_CH2, currently assigned to MOS PWM input for lamp 2."
        elif canonical in {"PB8", "PB9"}:
            category, group = "bus", "i2c"
            purpose = "Project I²C bus for AS7343, TSL2591 and the dual INA219 monitor."
        elif "QSPI" in upper:
            category, group = "reserved", "qspi"
            caution = "Reserved for the onboard W25Q64 QSPI flash; do not reuse while that storage is enabled."

    if device_id == "f103":
        if canonical.startswith("PA0"):
            category, group = "pwm", "pixel"
            purpose = "Verified PA0 output for the SK6812/WS2812 serial data chain."
            usage = "PA0 → optional 220–470 Ω series resistor → first pixel DIN; first DOUT → second DIN; pixel power is wired in parallel."
            caution = "The pixel supply and STM32 must share GND. Do not connect DOUT back to DOUT."
        if "BOOT" in upper:
            category, group = "reserved", "boot"
            caution = "This level is sampled during reset and can change the boot source. Keep the documented default for normal Flash boot."

    if device_id == "esp32":
        if canonical in {"IO35", "IO36", "IO37"}:
            category, group = "reserved", "psram"
            purpose = "Not available on the N8R8 module: connected internally to 8 MB octal PSRAM."
            usage = "Leave unconnected even though the development-board header and silkscreen expose the position."
            caution = "Official module documentation says IO35/36/37 cannot be used for other functions on R8 variants."
        elif canonical in {"IO0", "IO3", "IO45", "IO46"}:
            category, group = "reserved", "strap"
            purpose = "Boot strapping pin sampled at reset, then available only with design care."
            usage = "Avoid external circuits that force the wrong level during reset. GPIO0 controls download boot; GPIO3 selects JTAG source; GPIO45/46 affect startup configuration."
            caution = "A fixed external pull resistor or driven peripheral can prevent booting. IO46 should be treated as input-only."
        elif canonical in {"IO19", "IO20"}:
            category, group = "bus", "usb"
            purpose = "Native USB signal: IO19 is D− and IO20 is D+. They are also ADC2 inputs when USB is unused."
            caution = "Do not attach general loads while native USB/JTAG/OTG uses this pair."
        elif canonical == "IO38":
            category, group = "pwm", "rgb"
            purpose = "GPIO38 is connected to the onboard WS2812B RGB LED data input and also appears at the header."
            caution = "External use shares this net with the onboard addressable LED."
        elif canonical in {"IO8", "IO9"}:
            category, group = "bus", "i2c"
            purpose = "Current project assignment: IO8=SDA and IO9=SCL for the TSL2591. ESP32's GPIO matrix can route I²C elsewhere if firmware changes."

    pin.update({
        "category": category,
        "group": group,
        "purpose": pin.get("purpose", purpose),
        "usage": pin.get("usage", usage),
        "electronics": pin.get("electronics", electronics),
        "caution": pin.get("caution", caution),
        "mode": mode,
    })
    return pin


class PinItem(QGraphicsObject):
    hovered = Signal(object)
    chosen = Signal(object)

    def __init__(self, pin: dict, width: float = 164.0) -> None:
        super().__init__()
        self.pin = pin
        self.width = width
        self.is_hovered = False
        self.is_selected = False
        self.is_related = False
        self.setAcceptHoverEvents(True)
        self.setToolTip(self._tooltip())
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def boundingRect(self) -> QRectF:  # noqa: N802
        return QRectF(0, 0, self.width, 24)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        color = COLORS.get(self.pin["category"], COLORS["gpio"])
        if self.is_selected:
            color = color.lighter(112)
            pen = QPen(QColor("#13242C"), 3)
        elif self.is_hovered:
            color = color.lighter(118)
            pen = QPen(QColor("#1E8277"), 2)
        elif self.is_related:
            pen = QPen(QColor("#D3973C"), 2)
        else:
            pen = QPen(color.darker(145), 1)
        painter.setPen(pen)
        painter.setBrush(color)
        painter.drawRoundedRect(self.boundingRect(), 7, 7)
        painter.setPen(QColor("#FFFFFF") if self.pin["category"] in {"ground", "reserved"} else INK)
        painter.setFont(QFont("Cascadia Mono", 8, QFont.Weight.DemiBold))
        number = self.pin.get("number") or self.pin.get("position")
        prefix = f"{number:>2}  " if isinstance(number, int) else ""
        painter.drawText(self.boundingRect().adjusted(8, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, prefix + str(self.pin.get("pin", "")))

    def hoverEnterEvent(self, event) -> None:  # noqa: N802
        self.is_hovered = True
        self.update()
        self.hovered.emit(self.pin)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:  # noqa: N802
        self.is_hovered = False
        self.update()
        self.hovered.emit(None)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.chosen.emit(self.pin)
        event.accept()

    def set_marks(self, selected: bool, related: bool) -> None:
        self.is_selected = selected
        self.is_related = related
        self.update()

    def _tooltip(self) -> str:
        return (
            f"<b>{html.escape(str(self.pin.get('pin', '')))}</b><br>"
            f"用途: {html.escape(str(self.pin['purpose']))}<br>"
            f"接法: {html.escape(str(self.pin['usage']))}<br>"
            f"<span style='color:#b43b49'>注意: {html.escape(str(self.pin['caution']))}</span>"
        )


class PinScene(QGraphicsScene):
    hovered = Signal(object)
    selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.items_by_pin: list[PinItem] = []
        self.profile: dict = {}
        self.locked_pin: dict | None = None

    def load_profile(self, profile: dict) -> None:
        self.clear()
        self.items_by_pin.clear()
        self.profile = profile
        self.locked_pin = None
        pins = [_describe(profile["device_id"], item) for item in profile.get("pins", [])]
        if profile["device_id"] == "h7":
            self._draw_headers(pins, columns=2, scene_height=1120)
        elif profile["device_id"] == "esp32":
            self._draw_headers(pins, columns=1, scene_height=790)
        else:
            self._draw_package(pins)

    def _board(self, x: float, y: float, width: float, height: float) -> None:
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, width, height), 22, 22)
        board = self.addPath(path, QPen(QColor("#10252E"), 2), QColor("#1E343D"))
        board.setZValue(-2)
        title = self.addText(self.profile.get("name", "Device"), QFont("Bahnschrift", 16, QFont.Weight.Bold))
        title.setDefaultTextColor(QColor("#F9F5E9"))
        title.setTextWidth(width - 30)
        title.setPos(x + 15, y + 20)
        subtitle = self.addText(self._subtitle(), QFont("Aptos", 9))
        subtitle.setDefaultTextColor(QColor("#9FC0C8"))
        subtitle.setTextWidth(width - 34)
        subtitle.setPos(x + 17, y + 60)

    def _subtitle(self) -> str:
        device_id = self.profile.get("device_id")
        if device_id == "esp32":
            return "2×22 header · 3.3 V logic · 8 MB Flash + 8 MB OSPI PSRAM\nCH343 UART · native USB/JTAG · onboard GPIO38 RGB"
        if device_id == "h7":
            return "dual-row expansion headers · 3.3 V logic\nPB8/PB9 I²C · PA0/PA1 synchronized TIM2 PWM"
        return "logical LQFP48 package view · carrier header not yet identified\nPA0 pixel data · PA13/PA14 SWD"

    def _add_pin(self, pin: dict, x: float, y: float, width: float = 164) -> None:
        item = PinItem(pin, width)
        item.setPos(x, y)
        item.hovered.connect(self._hover)
        item.chosen.connect(self._choose)
        self.addItem(item)
        self.items_by_pin.append(item)

    def _draw_headers(self, pins: list[dict], columns: int, scene_height: int) -> None:
        left = [pin for pin in pins if str(pin.get("side", "")).lower() == "left"]
        right = [pin for pin in pins if str(pin.get("side", "")).lower() == "right"]
        rows = max((len(left) + columns - 1) // columns, (len(right) + columns - 1) // columns)
        board_y = 42
        board_h = max(650, rows * 32 + 100)
        self.setSceneRect(0, 0, 1120, max(scene_height, int(board_h + 90)))
        self._board(405, board_y, 310, board_h)
        if self.profile.get("device_id") == "esp32":
            module = self.addRect(QRectF(445, 155, 230, 180), QPen(QColor("#98A6AC"), 1), QColor("#D8D3C5"))
            module.setZValue(-1)
            antenna = self.addText("PCB ANTENNA\nESP32-S3-WROOM-1-N8R8", QFont("Cascadia Mono", 9, QFont.Weight.Bold))
            antenna.setDefaultTextColor(INK)
            antenna.setPos(465, 195)
            usb = self.addText("USB-C · CH343 + CH334", QFont("Cascadia Mono", 9))
            usb.setDefaultTextColor(QColor("#F2C166"))
            usb.setPos(465, board_y + board_h - 70)
        else:
            chip = self.addRect(QRectF(472, 185, 176, 176), QPen(QColor("#AFC5CC"), 2), QColor("#15232A"))
            chip.setZValue(-1)
            text = self.addText("STM32H743IIT6\nCortex-M7 · 480 MHz", QFont("Cascadia Mono", 10, QFont.Weight.Bold))
            text.setDefaultTextColor(QColor("#E9B44C"))
            text.setPos(490, 235)
        for index, pin in enumerate(left):
            row, lane = divmod(index, columns)
            self._add_pin(pin, 40 + lane * 174, 86 + row * 32)
        for index, pin in enumerate(right):
            row, lane = divmod(index, columns)
            self._add_pin(pin, 742 + lane * 174, 86 + row * 32)

    def _draw_package(self, pins: list[dict]) -> None:
        self.setSceneRect(0, 0, 1120, 900)
        self._board(390, 180, 340, 520)
        chip = self.addRect(QRectF(455, 310, 210, 210), QPen(QColor("#AFC5CC"), 2), QColor("#101B21"))
        chip.setZValue(-1)
        dot = self.addEllipse(QRectF(474, 330, 14, 14), QPen(Qt.PenStyle.NoPen), QColor("#E9B44C"))
        dot.setZValue(0)
        label = self.addText("STM32F103\nLQFP48\nlogical package order", QFont("Cascadia Mono", 11, QFont.Weight.Bold))
        label.setDefaultTextColor(QColor("#F9F5E9"))
        label.setPos(500, 376)
        for index, pin in enumerate(pins[:24]):
            self._add_pin(pin, 55, 75 + index * 32, 205)
        for index, pin in enumerate(pins[24:48]):
            self._add_pin(pin, 860, 75 + index * 32, 205)
        note = self.addText("Pins 1–24                         Pins 25–48\nPackage sequence view; physical carrier-board headers remain unverified.", QFont("Aptos", 10))
        note.setDefaultTextColor(QColor("#6C7A82"))
        note.setPos(330, 790)

    def _hover(self, pin: object) -> None:
        self.hovered.emit(pin)

    def _choose(self, pin: dict) -> None:
        self.locked_pin = pin
        group = pin.get("group")
        canonical = _canonical(pin)
        for item in self.items_by_pin:
            item.set_marks(_canonical(item.pin) == canonical, bool(group and item.pin.get("group") == group))
        self.selected.emit(pin)


class PinAtlasView(QGraphicsView):
    def __init__(self, scene: PinScene) -> None:
        super().__init__(scene)
        self._auto_fit = True
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(PAPER)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

    def reset_view(self) -> None:
        self._auto_fit = True
        self.resetTransform()
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor: float) -> None:
        self._auto_fit = False
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._auto_fit:
            self.reset_view()

    def wheelEvent(self, event) -> None:  # noqa: N802
        self.zoom(1.14 if event.angleDelta().y() > 0 else 1 / 1.14)
        event.accept()


class InteractivePinAtlas(QWidget):
    def __init__(self) -> None:
        super().__init__()
        profile_dir = Path(__file__).resolve().parents[1] / "device_profiles"
        self.profiles = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in profile_dir.glob("*.json")
        }
        self.current_id = "h7"
        self.locked = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        self.board_label = QLabel()
        self.board_label.setStyleSheet("font-family:'Bahnschrift';font-size:16px;font-weight:700;")
        toolbar.addWidget(self.board_label)
        toolbar.addStretch()
        for text, callback in (("−", lambda: self.view.zoom(1 / 1.2)), ("100%", self._reset), ("+", lambda: self.view.zoom(1.2))):
            button = QPushButton(text)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        root.addLayout(toolbar)

        body = QHBoxLayout()
        self.scene = PinScene()
        self.view = PinAtlasView(self.scene)
        self.scene.hovered.connect(self._hovered)
        self.scene.selected.connect(self._selected)
        body.addWidget(self.view, 1)

        detail = QFrame()
        detail.setObjectName("card")
        detail.setMinimumWidth(330)
        detail.setMaximumWidth(390)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(20, 18, 20, 18)
        self.pin_title = QLabel("Hover a pin")
        self.pin_title.setStyleSheet("font-family:'Bahnschrift';font-size:21px;font-weight:700;")
        detail_layout.addWidget(self.pin_title)
        self.pin_meta = QLabel()
        self.pin_meta.setObjectName("muted")
        self.pin_meta.setWordWrap(True)
        detail_layout.addWidget(self.pin_meta)
        self.pin_body = QLabel()
        self.pin_body.setWordWrap(True)
        self.pin_body.setTextFormat(Qt.TextFormat.RichText)
        self.pin_body.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_layout.addWidget(self.pin_body, 1)
        self.source_button = QPushButton("Open authoritative source")
        self.source_button.clicked.connect(self._open_source)
        detail_layout.addWidget(self.source_button)
        body.addWidget(detail)
        root.addLayout(body, 1)

        legend = QHBoxLayout()
        for key, text in (("gpio", "GPIO"), ("analog", "ADC/Touch"), ("bus", "Bus"), ("pwm", "PWM"), ("debug", "Debug"), ("power", "Power"), ("ground", "Ground"), ("reserved", "Reserved / caution")):
            chip = QLabel(f"  {text}  ")
            color = COLORS[key].name()
            foreground = "#FFFFFF" if key in {"ground", "reserved"} else "#17212B"
            chip.setStyleSheet(f"background:{color};color:{foreground};border-radius:7px;padding:4px 6px;")
            legend.addWidget(chip)
        legend.addStretch()
        root.addLayout(legend)
        self._load("h7")

    def set_mode(self, mode: str) -> None:
        if "H7" in mode:
            device_id = "h7"
        elif "F103" in mode:
            device_id = "f103"
        else:
            device_id = "esp32"
        self._load(device_id)

    def _load(self, device_id: str) -> None:
        self.current_id = device_id
        self.locked = False
        profile = self.profiles[device_id]
        self.board_label.setText(profile["name"])
        self.scene.load_profile(profile)
        self.view.reset_view()
        self._show_overview()

    def _reset(self) -> None:
        self.view.reset_view()

    def _hovered(self, pin: object) -> None:
        if self.locked:
            return
        if isinstance(pin, dict):
            self._show_pin(pin, locked=False)
        else:
            self._show_overview()

    def _selected(self, pin: dict) -> None:
        self.locked = True
        self._show_pin(pin, locked=True)

    def _show_overview(self) -> None:
        profile = self.profiles[self.current_id]
        self.pin_title.setText("Hover or click a pin")
        complete = "complete" if profile.get("inventory_complete") else "partially verified"
        self.pin_meta.setText(f"{len(profile.get('pins', []))} inventoried pins · {complete}")
        self.pin_body.setText(
            "<b>How to use this atlas</b><br>"
            "Hover for a quick electrical lesson. Click to lock the explanation and highlight related pins. "
            "Use the mouse wheel to zoom and drag the canvas to pan.<br><br>"
            "<b>First rule</b><br>Voltage is measured relative to GND. Share signal ground between separately powered boards, "
            "but power high-current lamps from their external supply and driver, never from a GPIO."
        )
        self.source_button.setEnabled(bool(profile.get("source_url")))

    def _show_pin(self, pin: dict, locked: bool) -> None:
        state = "clicked · locked" if locked else "hover preview"
        location = pin.get("side", "")
        number = pin.get("number") or pin.get("position") or "—"
        self.pin_title.setText(str(pin.get("pin", "Pin")))
        self.pin_meta.setText(f"{state} · {location} · position {number} · {pin.get('category', 'gpio')}")
        self.pin_body.setText(
            f"<b>Purpose / 用途</b><br>{html.escape(str(pin['purpose']))}<br><br>"
            f"<b>How to connect / 接法</b><br>{html.escape(str(pin['usage']))}<br><br>"
            f"<b>Electronics / 电子学</b><br>{html.escape(str(pin['electronics']))}<br><br>"
            f"<b style='color:#B43B49'>Caution / 注意</b><br>{html.escape(str(pin['caution']))}<br><br>"
            f"<b>Current project role</b><br>{html.escape(str(pin.get('role', 'GPIO')))} · {html.escape(str(pin.get('mode', 'unassigned')))}"
        )

    def _open_source(self) -> None:
        url = self.profiles[self.current_id].get("source_url")
        if url:
            QDesktopServices.openUrl(QUrl(url))
