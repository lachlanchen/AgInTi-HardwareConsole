from __future__ import annotations

import sys
import ctypes
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QFont, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileSystemModel,
    QFrame,
    QGridLayout,
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QGraphicsOpacityEffect,
)

from .backend import HardwareBackend
from .config import BOARD_COPY, FirmwareProfile, discover_paths, firmware_profiles
from .pin_atlas import InteractivePinAtlas
from .widgets import CodeEditor, HistoryPlot, MetricCard, SpectrumPlot, StatusPill


ALLOWED_SOURCE_SUFFIXES = {
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".ino",
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".ld",
    ".s",
    ".ps1",
}


STYLE = r"""
QWidget { color:#17212B; font-family:"Aptos"; font-size:13px; }
QMainWindow, QWidget#root { background:#F3F1EA; }
QFrame#sidebar { background:#17242C; border:none; }
QLabel#brandKicker { color:#70D2C3; font-family:"Cascadia Mono"; font-size:10px; font-weight:700; letter-spacing:2px; }
QLabel#brandTitle { color:#F9F5E9; font-family:"Bahnschrift"; font-size:23px; font-weight:700; }
QLabel#brandSub { color:#8EA2AA; font-size:11px; }
QPushButton#navButton { color:#AFC0C5; text-align:left; border:0; border-radius:10px; padding:11px 14px; font-family:"Bahnschrift"; font-size:13px; }
QPushButton#navButton:hover { background:#22353E; color:#FFFFFF; }
QPushButton#navButton:checked { background:#E9B44C; color:#18242B; font-weight:700; }
QLabel#pageTitle { font-family:"Bahnschrift"; font-size:24px; font-weight:700; }
QLabel#pageSubtitle { color:#6E7982; font-size:12px; }
QFrame#card, QFrame#metricCard { background:#FFFFFF; border:1px solid #E3E5E2; border-radius:16px; }
QFrame#hero { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #17343A,stop:0.55 #1D5050,stop:1 #D3973C); border-radius:20px; }
QLabel#heroTitle { color:#FFFFFF; font-family:"Bahnschrift"; font-size:25px; font-weight:700; }
QLabel#heroText { color:#D8E5E2; font-size:13px; }
QLabel#sectionTitle { font-family:"Bahnschrift"; font-size:16px; font-weight:700; }
QLabel#muted { color:#748089; }
QLabel#metricTitle { color:#78848C; font-family:"Cascadia Mono"; font-size:9px; font-weight:700; }
QLabel#metricValue { font-family:"Bahnschrift"; font-size:24px; font-weight:700; }
QLabel#metricUnit { color:#76828A; font-size:11px; padding-bottom:3px; }
QPushButton { background:#FFFFFF; border:1px solid #D6DBDC; border-radius:10px; padding:8px 14px; font-weight:600; }
QPushButton:hover { border-color:#22B8A7; background:#F2FBF9; }
QPushButton:pressed { background:#DDF6F1; }
QPushButton#primary { background:#1E8277; border-color:#1E8277; color:#FFFFFF; }
QPushButton#primary:hover { background:#176E65; }
QPushButton#danger { background:#D84D5B; border-color:#D84D5B; color:#FFFFFF; font-family:"Bahnschrift"; font-weight:700; }
QPushButton#danger:hover { background:#B93E4B; }
QPushButton#amber { background:#E6A23C; border-color:#E6A23C; color:#17212B; }
QComboBox, QSpinBox, QDoubleSpinBox { background:#FFFFFF; border:1px solid #D3D9DA; border-radius:9px; padding:7px 10px; min-height:20px; }
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border:1px solid #22B8A7; }
QPlainTextEdit, QTreeView { background:#FFFFFF; border:1px solid #DDE1E2; border-radius:12px; selection-background-color:#CDEEE8; }
QPlainTextEdit#log { background:#142129; color:#DCE8E7; border:0; font-family:"Cascadia Mono"; font-size:10px; }
QTreeView { padding:6px; }
QHeaderView::section { background:#EBEFEE; border:0; padding:6px; font-weight:700; }
QSlider::groove:horizontal { height:6px; border-radius:3px; background:#DCE2E2; }
QSlider::sub-page:horizontal { background:#22B8A7; border-radius:3px; }
QSlider::handle:horizontal { width:18px; margin:-6px 0; border-radius:9px; background:#FFFFFF; border:2px solid #168878; }
QScrollArea { border:0; background:transparent; }
QSplitter::handle { background:#E2E5E4; width:2px; }
QToolTip { background:#17242C; color:#FFFFFF; border:0; padding:6px; }
"""


class BoardCard(QFrame):
    def __init__(self, board_id: str) -> None:
        super().__init__()
        self.setObjectName("card")
        copy = BOARD_COPY[board_id]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)
        top = QHBoxLayout()
        name = QLabel(copy["name"])
        name.setObjectName("sectionTitle")
        self.status = StatusPill()
        top.addWidget(name)
        top.addStretch()
        top.addWidget(self.status)
        layout.addLayout(top)
        subtitle = QLabel(copy["subtitle"])
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        usb = QLabel(copy["usb"])
        usb.setStyleSheet("font-family:'Cascadia Mono'; font-size:10px; color:#75828A;")
        layout.addWidget(usb)
        self.detail = QLabel("Waiting for device refresh")
        self.detail.setObjectName("muted")
        layout.addWidget(self.detail)

    def set_state(self, online: bool, detail: str) -> None:
        self.status.set_online(online)
        self.detail.setText(detail)


class HardwareConsole(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.paths = discover_paths()
        self.profiles = dict(firmware_profiles(self.paths))
        self.backend = HardwareBackend(self.paths, self.profiles)
        self.current_file: Path | None = None
        self.board_cards: dict[str, BoardCard] = {}
        self.board_pills: dict[str, StatusPill] = {}
        self.nav_buttons: list[QPushButton] = []
        self.page_titles = ["Overview", "Firmware", "Lamp & Pixels", "Sensors", "Digital Twin", "Interactive Pins", "Source Files", "Activity Log"]
        self.twin_model: dict = {}
        self.tsl_visible_history: list[float] = []
        self.setWindowTitle("AgInTi Hardware Console")
        self.resize(1540, 960)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._connect_backend()
        self._set_page(0)
        self.backend.refresh_twin()
        self.log("Hardware Console ready. Device probing is manual and safe while boards are unplugged.")

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(236)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 28, 22, 22)
        side.setSpacing(7)
        kicker = QLabel("AGINTI · LAB SYSTEMS")
        kicker.setObjectName("brandKicker")
        title = QLabel("Hardware\nConsole")
        title.setObjectName("brandTitle")
        subtitle = QLabel("FLASH · CONTROL · MEASURE")
        subtitle.setObjectName("brandSub")
        side.addWidget(kicker)
        side.addWidget(title)
        side.addWidget(subtitle)
        side.addSpacing(24)

        nav_labels = ["Overview", "Firmware", "Lamp & Pixels", "Sensors", "Digital Twin", "Interactive Pins", "Source Files", "Activity Log"]
        for index, label in enumerate(nav_labels):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self._set_page(page))
            side.addWidget(button)
            self.nav_buttons.append(button)
        side.addStretch()
        version = QLabel("v0.1 · offline-safe\nDualLampHI / stm32dev")
        version.setObjectName("brandSub")
        side.addWidget(version)
        outer.addWidget(sidebar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(30, 22, 30, 24)
        body_layout.setSpacing(16)
        header = QHBoxLayout()
        heading = QVBoxLayout()
        self.page_title = QLabel("Overview")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("One surface for firmware, light, spectra and wiring")
        self.page_subtitle.setObjectName("pageSubtitle")
        heading.addWidget(self.page_title)
        heading.addWidget(self.page_subtitle)
        header.addLayout(heading)
        header.addStretch()
        for board_id, short in (("h7", "H7"), ("f103", "F103"), ("esp32", "ESP32")):
            pill = StatusPill(f"{short} OFF")
            pill.set_online(False, f"{short} OFF")
            self.board_pills[board_id] = pill
            header.addWidget(pill)
        refresh = QPushButton("Refresh devices")
        refresh.clicked.connect(self.backend.refresh_devices)
        header.addWidget(refresh)
        all_off = QPushButton("ALL LAMPS OFF")
        all_off.setObjectName("danger")
        all_off.clicked.connect(lambda: self.backend.lamp("off", 0, 0))
        header.addWidget(all_off)
        body_layout.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._overview_page())
        self.stack.addWidget(self._firmware_page())
        self.stack.addWidget(self._control_page())
        self.stack.addWidget(self._sensor_page())
        self.stack.addWidget(self._twin_page())
        self.stack.addWidget(self._pins_page())
        self.stack.addWidget(self._files_page())
        self.stack.addWidget(self._logs_page())
        body_layout.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        QShortcut(QKeySequence("Ctrl+Shift+X"), self, activated=lambda: self.backend.lamp("off", 0, 0))
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_file)

    def _scroll(self, content: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(content)
        return area

    def _overview_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        copy = QVBoxLayout()
        hero_title = QLabel("A coherent bench, not a pile of boards.")
        hero_title.setObjectName("heroTitle")
        hero_text = QLabel("Flash three MCU families, pulse lamps safely, inspect live spectra,\nand trace every wire from one deliberate control surface.")
        hero_text.setObjectName("heroText")
        copy.addWidget(hero_title)
        copy.addWidget(hero_text)
        hero_layout.addLayout(copy)
        hero_layout.addStretch()
        quick_off = QPushButton("Emergency off  Ctrl+Shift+X")
        quick_off.setObjectName("danger")
        quick_off.clicked.connect(lambda: self.backend.lamp("off", 0, 0))
        hero_layout.addWidget(quick_off)
        layout.addWidget(hero)

        board_grid = QGridLayout()
        board_grid.setSpacing(14)
        for column, board_id in enumerate(("h7", "f103", "esp32")):
            card = BoardCard(board_id)
            self.board_cards[board_id] = card
            board_grid.addWidget(card, 0, column)
        layout.addLayout(board_grid)

        lower = QHBoxLayout()
        actions = self._card("Safe quick actions", "All actions are timed unless you explicitly enable hold.")
        action_layout = actions.layout()
        row = QHBoxLayout()
        for label, command in (("Lamp 1 · 3 s", "lamp1"), ("Lamp 2 · 3 s", "lamp2"), ("Both · 3 s", "both")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, cmd=command: self.backend.lamp(cmd, 52428, 3.0))
            row.addWidget(button)
        off = QPushButton("Off")
        off.setObjectName("danger")
        off.clicked.connect(lambda: self.backend.lamp("off", 0, 0))
        row.addWidget(off)
        action_layout.addLayout(row)
        lower.addWidget(actions, 1)

        topology = self._card("Known-good topology", "The ground wire is part of the signal path.")
        topology_text = QLabel("PB8 → SCL    PB9 → SDA\nPA0 → MOS 1  PA1 → MOS 2\nSTM32 GND = MOS GND = Monitor GND = lamp supply −")
        topology_text.setStyleSheet("font-family:'Cascadia Mono'; color:#44545D; line-height:1.5;")
        topology.layout().addWidget(topology_text)
        lower.addWidget(topology, 1)
        layout.addLayout(lower)
        layout.addStretch()
        return self._scroll(content)

    def _card(self, title: str, subtitle: str = "") -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        if subtitle:
            detail = QLabel(subtitle)
            detail.setObjectName("muted")
            detail.setWordWrap(True)
            layout.addWidget(detail)
        return card

    def _firmware_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        selector = self._card("Firmware profiles", "Commands are explicit, logged and scoped to the selected board.")
        form = QGridLayout()
        form.addWidget(QLabel("Profile"), 0, 0)
        self.profile_combo = QComboBox()
        for profile_id, profile in self.profiles.items():
            self.profile_combo.addItem(profile.title, profile_id)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        form.addWidget(self.profile_combo, 0, 1, 1, 3)
        form.addWidget(QLabel("ESP32 port"), 1, 0)
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setPlaceholderText("Offline / select after connection")
        form.addWidget(self.port_combo, 1, 1, 1, 3)
        self.profile_description = QLabel()
        self.profile_description.setWordWrap(True)
        self.profile_description.setObjectName("muted")
        form.addWidget(self.profile_description, 2, 0, 1, 4)
        build = QPushButton("Build only")
        build.clicked.connect(lambda: self._run_selected_profile("build"))
        flash = QPushButton("Flash only")
        flash.setObjectName("amber")
        flash.clicked.connect(lambda: self._run_selected_profile("flash"))
        both = QPushButton("Build + flash")
        both.setObjectName("primary")
        both.clicked.connect(lambda: self._run_selected_profile("build_flash"))
        form.addWidget(build, 3, 1)
        form.addWidget(flash, 3, 2)
        form.addWidget(both, 3, 3)
        selector.layout().addLayout(form)
        layout.addWidget(selector)

        grid = QGridLayout()
        for index, profile in enumerate(self.profiles.values()):
            card = self._card(profile.title, profile.description)
            board = QLabel(profile.board_id.upper())
            board.setStyleSheet("font-family:'Cascadia Mono'; color:#168878; font-weight:700;")
            path = QLabel(str(profile.source_dir))
            path.setWordWrap(True)
            path.setStyleSheet("font-family:'Cascadia Mono'; font-size:9px; color:#75828A;")
            card.layout().addWidget(board)
            card.layout().addWidget(path)
            use = QPushButton("Select profile")
            use.clicked.connect(lambda checked=False, pid=profile.profile_id: self._select_profile(pid))
            card.layout().addWidget(use)
            grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addStretch()
        self._profile_changed()
        return self._scroll(content)

    def _control_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        lamp = self._card("Dual MOS lamp control", "H7 TIM2: PA0/CCR1 → lamp 1, PA1/CCR2 → lamp 2. Carrier remains below the YYNMOS 500 Hz limit.")
        lamp_grid = QGridLayout()
        lamp_grid.addWidget(QLabel("16-bit PWM duty"), 0, 0)
        self.duty_slider = QSlider(Qt.Orientation.Horizontal)
        self.duty_slider.setRange(0, 65535)
        self.duty_slider.setValue(52428)
        self.duty_spin = QSpinBox()
        self.duty_spin.setRange(0, 65535)
        self.duty_spin.setValue(52428)
        self.duty_slider.valueChanged.connect(self.duty_spin.setValue)
        self.duty_spin.valueChanged.connect(self.duty_slider.setValue)
        lamp_grid.addWidget(self.duty_slider, 0, 1, 1, 3)
        lamp_grid.addWidget(self.duty_spin, 0, 4)
        lamp_grid.addWidget(QLabel("Pulse duration"), 1, 0)
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0.05, 30.0)
        self.duration.setValue(3.0)
        self.duration.setSuffix(" s")
        lamp_grid.addWidget(self.duration, 1, 1)
        self.hold_check = QCheckBox("Explicit hold mode")
        self.hold_check.setToolTip("Persistent light can heat tungsten lamps. Timed pulse is the safe default.")
        lamp_grid.addWidget(self.hold_check, 1, 2, 1, 2)
        controls = QHBoxLayout()
        for label, command in (("Lamp 1", "lamp1"), ("Lamp 2", "lamp2"), ("Both", "both")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, cmd=command: self._lamp_command(cmd))
            controls.addWidget(button)
        off = QPushButton("ALL OFF")
        off.setObjectName("danger")
        off.clicked.connect(lambda: self.backend.lamp("off", 0, 0))
        controls.addWidget(off)
        lamp_grid.addLayout(controls, 2, 0, 1, 5)
        lamp.layout().addLayout(lamp_grid)
        layout.addWidget(lamp)

        pixels = self._card("Addressable pixel controller", "F103 PA0 drives a DIN→DOUT chain. Firmware descriptors distinguish SK6812 RGBW (32 bit) from WS2812B RGB (24 bit).")
        pixel_row = QHBoxLayout()
        for text, profile_id in (("Red / green static", "f103_static"), ("0 → 255 → 0 range", "f103_ramp"), ("RGBW color cycle", "f103_cycle")):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, pid=profile_id: self.backend.run_profile(pid, "build_flash"))
            pixel_row.addWidget(button)
        pixels.layout().addLayout(pixel_row)
        note = QLabel("Future calibrated LUTs should be generated from H7 AS7343 + TSL2591 data. Addressable pixels remain 8-bit per channel; temporal dithering may create unwanted event-camera activity.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        pixels.layout().addWidget(note)
        layout.addWidget(pixels)
        layout.addStretch()
        return self._scroll(content)

    def _sensor_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        toolbar = QHBoxLayout()
        self.sensor_pills = {name: StatusPill(name.upper()) for name in ("as7343", "tsl2591", "monitor1", "monitor2")}
        for name, pill in self.sensor_pills.items():
            pill.set_online(False, f"{name.upper()} OFF")
            toolbar.addWidget(pill)
        toolbar.addStretch()
        self.auto_refresh = QCheckBox("Auto snapshot")
        self.auto_refresh.setChecked(False)
        toolbar.addWidget(self.auto_refresh)
        self.snapshot_interval = QSpinBox()
        self.snapshot_interval.setRange(1000, 10000)
        self.snapshot_interval.setValue(2500)
        self.snapshot_interval.setSuffix(" ms")
        self.snapshot_interval.valueChanged.connect(self._update_snapshot_timer)
        toolbar.addWidget(self.snapshot_interval)
        refresh = QPushButton("Read H7 now")
        refresh.setObjectName("primary")
        refresh.clicked.connect(self.backend.read_snapshot)
        toolbar.addWidget(refresh)
        layout.addLayout(toolbar)

        metrics = QGridLayout()
        self.metric_visible = MetricCard("TSL visible", "--", "counts")
        self.metric_full = MetricCard("TSL full", "--", "counts")
        self.metric_power1 = MetricCard("Lamp 1 power", "--", "mW")
        self.metric_power2 = MetricCard("Lamp 2 power", "--", "mW")
        self.metric_current1 = MetricCard("Lamp 1 current", "--", "mA")
        self.metric_current2 = MetricCard("Lamp 2 current", "--", "mA")
        for index, card in enumerate((self.metric_visible, self.metric_full, self.metric_power1, self.metric_power2, self.metric_current1, self.metric_current2)):
            metrics.addWidget(card, index // 3, index % 3)
        layout.addLayout(metrics)

        chart_toolbar = QHBoxLayout()
        chart_toolbar.addWidget(QLabel("Spectrum scale"))
        self.spectrum_mode = QComboBox()
        self.spectrum_mode.addItems(["Auto", "Fixed 16-bit", "Normalize"])
        chart_toolbar.addWidget(self.spectrum_mode)
        chart_toolbar.addStretch()
        layout.addLayout(chart_toolbar)
        self.spectrum_plot = SpectrumPlot()
        self.spectrum_mode.currentTextChanged.connect(self.spectrum_plot.set_mode)
        layout.addWidget(self.spectrum_plot)
        plots = QHBoxLayout()
        self.tsl_plot = HistoryPlot("TSL2591 intensity history", ("visible", "infrared"))
        self.power_plot = HistoryPlot("Monitor HAT power history", ("lamp 1", "lamp 2"))
        plots.addWidget(self.tsl_plot, 1)
        plots.addWidget(self.power_plot, 1)
        layout.addLayout(plots)

        self.snapshot_timer = QTimer(self)
        self.snapshot_timer.timeout.connect(self._auto_snapshot)
        self.auto_refresh.toggled.connect(self._update_snapshot_timer)
        return self._scroll(content)

    def _pins_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Physical device"))
        selector = QComboBox()
        selector.addItems([
            "H7 · Geek STM32H743IIT6 · dual-row headers",
            "F103 · medium-density LQFP48 · verified controller",
            "ESP32 · Waveshare ESP32-S3-DEV-KIT-N8R8 · 2×22",
        ])
        controls.addWidget(selector)
        controls.addStretch()
        warning = QLabel("Hover to learn · click to lock · wheel to zoom · drag to pan")
        warning.setObjectName("muted")
        controls.addWidget(warning)
        layout.addLayout(controls)
        pinmap = InteractivePinAtlas()
        selector.currentTextChanged.connect(pinmap.set_mode)
        layout.addWidget(pinmap, 1)
        return page

    def _twin_page(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        header = self._card(
            "Hardware Task Manager",
            "A file-backed mirror of CPU resources, execution contexts, storage, pins, telemetry and control intent.",
        )
        row = QHBoxLayout()
        row.addWidget(QLabel("Device"))
        self.twin_device_combo = QComboBox()
        self.twin_device_combo.addItem("STM32H743 sensor head", "h7")
        self.twin_device_combo.addItem("STM32F103 pixel controller", "f103")
        self.twin_device_combo.addItem("ESP32-S3 N8R8", "esp32")
        self.twin_device_combo.currentIndexChanged.connect(self._render_twin)
        row.addWidget(self.twin_device_combo)
        row.addStretch()
        self.twin_path = QLabel("runtime/hardwarefs")
        self.twin_path.setStyleSheet("font-family:'Cascadia Mono'; color:#66757D;")
        row.addWidget(self.twin_path)
        refresh = QPushButton("Refresh mirror")
        refresh.clicked.connect(self.backend.refresh_twin)
        row.addWidget(refresh)
        header.layout().addLayout(row)
        layout.addWidget(header)

        resources = QGridLayout()
        self.twin_online = MetricCard("Connection", "OFFLINE", "")
        self.twin_cpu = MetricCard("CPU", "--", "")
        self.twin_clock = MetricCard("Configured clock", "--", "MHz")
        self.twin_ram = MetricCard("Total RAM", "--", "MiB")
        self.twin_flash = MetricCard("Nonvolatile", "--", "MiB")
        self.twin_pins = MetricCard("Pins inventoried", "--", "")
        for index, card in enumerate((self.twin_online, self.twin_cpu, self.twin_clock, self.twin_ram, self.twin_flash, self.twin_pins)):
            resources.addWidget(card, index // 3, index % 3)
        layout.addLayout(resources)

        tables = QSplitter(Qt.Orientation.Horizontal)
        task_card = self._card("Execution contexts", "Bare-metal contexts are not presented as fake operating-system threads.")
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["Context", "Kind", "Purpose", "State"])
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        task_card.layout().addWidget(self.task_table)
        tables.addWidget(task_card)

        storage_card = self._card("Memory & storage", "Capacity is declarative; live usage remains unknown until firmware exports it.")
        self.storage_table = QTableWidget(0, 4)
        self.storage_table.setHorizontalHeaderLabels(["Resource", "Kind", "Capacity", "Policy / base"])
        self.storage_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.storage_table.verticalHeader().setVisible(False)
        self.storage_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        storage_card.layout().addWidget(self.storage_table)
        tables.addWidget(storage_card)
        tables.setSizes([680, 560])
        layout.addWidget(tables, 1)

        pin_card = self._card("Complete pin inventory", "Role and mode come from tracked device-profile files; live level is materialized when available.")
        self.pin_table = QTableWidget(0, 5)
        self.pin_table.setHorizontalHeaderLabels(["Pin", "Header side", "Role", "Mode", "Live state"])
        self.pin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.pin_table.verticalHeader().setVisible(False)
        self.pin_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        pin_card.layout().addWidget(self.pin_table)
        layout.addWidget(pin_card, 2)
        return content

    def _files_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Source root"))
        self.file_root_combo = QComboBox()
        self.file_root_combo.addItem("DualLampHI firmware + scripts", str(self.paths.dual_lamp_root))
        self.file_root_combo.addItem("stm32dev firmware + scripts", str(self.paths.stm32dev_root))
        self.file_root_combo.currentIndexChanged.connect(self._file_root_changed)
        toolbar.addWidget(self.file_root_combo)
        toolbar.addStretch()
        self.file_label = QLabel("No file selected")
        self.file_label.setObjectName("muted")
        toolbar.addWidget(self.file_label)
        save = QPushButton("Save  Ctrl+S")
        save.setObjectName("primary")
        save.clicked.connect(self._save_file)
        toolbar.addWidget(save)
        layout.addLayout(toolbar)

        splitter = QSplitter()
        self.file_model = QFileSystemModel(self)
        self.file_model.setNameFilters([f"*{suffix}" for suffix in sorted(ALLOWED_SOURCE_SUFFIXES)])
        self.file_model.setNameFilterDisables(False)
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setHeaderHidden(True)
        for column in range(1, 4):
            self.file_tree.hideColumn(column)
        self.file_tree.clicked.connect(self._file_clicked)
        self.editor = CodeEditor()
        splitter.addWidget(self.file_tree)
        splitter.addWidget(self.editor)
        splitter.setSizes([330, 950])
        layout.addWidget(splitter, 1)
        self._file_root_changed()
        return page

    def _logs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        title = QLabel("Build, flash, OpenOCD and device activity")
        title.setObjectName("sectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch()
        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: self.log_view.clear())
        copy = QPushButton("Copy all")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.log_view.toPlainText()))
        toolbar.addWidget(clear)
        toolbar.addWidget(copy)
        layout.addLayout(toolbar)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("log")
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Cascadia Mono", 10))
        layout.addWidget(self.log_view, 1)
        return page

    def _connect_backend(self) -> None:
        self.backend.logLine.connect(self.log)
        self.backend.devicesChanged.connect(self._devices_changed)
        self.backend.snapshotChanged.connect(self._snapshot_changed)
        self.backend.twinChanged.connect(self._twin_changed)
        self.backend.taskStarted.connect(lambda label: self.log(f"START · {label}"))
        self.backend.taskFinished.connect(lambda label, ok: self.log(f"DONE  · {label}"))
        self.backend.taskError.connect(self._task_error)

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.page_title.setText(self.page_titles[index])
        subtitles = [
            "One surface for firmware, light, spectra and wiring",
            "Explicit profiles for H7, F103 and optional ESP32-S3",
            "Safe timed lamp pulses and addressable pixel firmware",
            "ST-Link snapshots without changing the H7 application image",
            "CPU, tasks, storage, pins and controls materialized as files",
            "Pin names, signal direction and power boundaries",
            "Edit approved firmware and scripts without leaving the console",
            "Every external command, result and hardware error",
        ]
        self.page_subtitle.setText(subtitles[index])
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        widget = self.stack.currentWidget()
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(150)
        animation.setStartValue(0.2)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: widget.setGraphicsEffect(None))
        self._page_animation = animation
        animation.start()

    def _devices_changed(self, state: dict) -> None:
        for board_id in ("h7", "f103", "esp32"):
            info = state.get(board_id, {})
            online = bool(info.get("online"))
            detail = str(info.get("detail", "Unknown"))
            self.board_cards[board_id].set_state(online, detail)
            short = board_id.upper()
            self.board_pills[board_id].set_online(online, f"{short} {'ON' if online else 'OFF'}")
        self.port_combo.clear()
        for port in state.get("ports", []):
            self.port_combo.addItem(f"{port['device']} · {port['description']}", port["device"])
        tools = state.get("tools", {})
        self.log("Tools · " + "  ".join(f"{name}={'yes' if present else 'no'}" for name, present in tools.items()))

    def _snapshot_changed(self, snapshot: dict) -> None:
        for name, online in snapshot["devices"].items():
            self.sensor_pills[name].set_online(bool(online), f"{name.upper()} {'ON' if online else 'OFF'}")
        tsl = snapshot["tsl2591"]
        monitor = snapshot["monitor"]
        lamp1 = monitor["lamp1"]
        lamp2 = monitor["lamp2"]
        self.metric_visible.set_value(tsl["visible"])
        self.metric_full.set_value(tsl["full"])
        self.metric_power1.set_value(lamp1["power_mW"])
        self.metric_power2.set_value(lamp2["power_mW"])
        self.metric_current1.set_value(lamp1["current_mA"])
        self.metric_current2.set_value(lamp2["current_mA"])
        self.spectrum_plot.set_values(snapshot["as7343"]["channels"])
        self.tsl_plot.append(tsl["visible"], tsl["infrared"])
        self.power_plot.append(lamp1["power_mW"], lamp2["power_mW"])
        self.log(f"Snapshot seq={snapshot['seq']} AS={snapshot['as7343']['samples']} TSL={tsl['samples']}")

    def _twin_changed(self, model: dict) -> None:
        self.twin_model = model
        self.twin_path.setText(model.get("runtime_root", "runtime/hardwarefs"))
        self._render_twin()

    def _render_twin(self) -> None:
        if not self.twin_model:
            return
        device_id = str(self.twin_device_combo.currentData())
        device = self.twin_model.get("devices", {}).get(device_id)
        if not device:
            return
        profile = device["profile"]
        state = device["state"]
        cpu = profile["cpu"]
        memory = profile.get("memory", [])
        ram_bytes = sum(item.get("capacity_bytes") or 0 for item in memory if item.get("kind") == "RAM")
        nonvolatile = sum(item.get("capacity_bytes") or 0 for item in memory if not item.get("volatile", False))
        self.twin_online.set_value("ONLINE" if state.get("online") else "OFFLINE")
        self.twin_cpu.set_value(f"{cpu.get('cores', '?')}× {cpu.get('architecture', 'CPU')}")
        self.twin_clock.set_value(cpu.get("configured_mhz") or "--")
        self.twin_ram.set_value(f"{ram_bytes / 1048576:.2f}")
        self.twin_flash.set_value(f"{nonvolatile / 1048576:.2f}")
        self.twin_pins.set_value(len(profile.get("pins", [])))

        tasks = state.get("tasks", profile.get("execution_contexts", []))
        self.task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [task.get("name", ""), task.get("kind", ""), task.get("purpose", ""), task.get("state", "offline")]
            for column, value in enumerate(values):
                self.task_table.setItem(row, column, QTableWidgetItem(str(value)))

        self.storage_table.setRowCount(len(memory))
        for row, item in enumerate(memory):
            capacity = item.get("capacity_bytes")
            capacity_text = "unknown" if capacity is None else f"{capacity / 1048576:.3f} MiB"
            detail = item.get("policy") or item.get("base") or ("present" if item.get("present") else "")
            values = [item.get("name", ""), item.get("kind", ""), capacity_text, detail]
            for column, value in enumerate(values):
                self.storage_table.setItem(row, column, QTableWidgetItem(str(value)))

        pins = profile.get("pins", [])
        self.pin_table.setRowCount(len(pins))
        live_controls = state.get("controls", {})
        for row, pin in enumerate(pins):
            live = "offline"
            if device_id == "h7" and pin.get("pin") == "PA0":
                live = str(live_controls.get("lamp1", "unknown"))
            elif device_id == "h7" and pin.get("pin") == "PA1":
                live = str(live_controls.get("lamp2", "unknown"))
            values = [pin.get("pin", ""), pin.get("side", ""), pin.get("role", ""), pin.get("mode", ""), live]
            for column, value in enumerate(values):
                self.pin_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _profile_changed(self) -> None:
        profile = self._selected_profile()
        self.profile_description.setText(
            f"{profile.description}\nSource: {profile.source_dir}\n{profile.safety_note}"
        )
        self.port_combo.setEnabled(profile.needs_port)

    def _selected_profile(self) -> FirmwareProfile:
        profile_id = self.profile_combo.currentData()
        return self.profiles[str(profile_id)]

    def _select_profile(self, profile_id: str) -> None:
        index = self.profile_combo.findData(profile_id)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def _run_selected_profile(self, action: str) -> None:
        profile = self._selected_profile()
        port = self.port_combo.currentData() or self.port_combo.currentText().split(" · ", 1)[0].strip()
        self.backend.run_profile(profile.profile_id, action, str(port))

    def _lamp_command(self, command: str) -> None:
        if self.hold_check.isChecked():
            answer = QMessageBox.warning(
                self,
                "Persistent lamp output",
                "Hold mode leaves the selected lamp on. Confirm that the lamp is supervised and thermally safe.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Ok:
                return
        self.backend.lamp(command, self.duty_spin.value(), self.duration.value(), self.hold_check.isChecked())

    def _update_snapshot_timer(self) -> None:
        self.snapshot_timer.setInterval(self.snapshot_interval.value())
        if self.auto_refresh.isChecked():
            self.snapshot_timer.start()
        else:
            self.snapshot_timer.stop()

    def _auto_snapshot(self) -> None:
        if self.auto_refresh.isChecked():
            self.backend.read_snapshot()

    def _file_root_changed(self) -> None:
        root = Path(str(self.file_root_combo.currentData())).resolve()
        root_index = self.file_model.setRootPath(str(root))
        self.file_tree.setRootIndex(root_index)
        self.current_file = None
        self.file_label.setText("No file selected")
        self.editor.clear()

    def _file_clicked(self, index) -> None:
        path = Path(self.file_model.filePath(index)).resolve()
        if not path.is_file() or path.suffix.lower() not in ALLOWED_SOURCE_SUFFIXES:
            return
        allowed_roots = (self.paths.dual_lamp_root.resolve(), self.paths.stm32dev_root.resolve())
        if not any(path.is_relative_to(root) for root in allowed_roots):
            return
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        self.current_file = path
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        try:
            display_path = path.relative_to(self.paths.projects_root)
        except ValueError:
            display_path = path
        self.file_label.setText(str(display_path))

    def _save_file(self) -> None:
        if self.current_file is None:
            return
        if self.current_file.suffix.lower() not in ALLOWED_SOURCE_SUFFIXES:
            return
        self.current_file.write_text(self.editor.toPlainText(), encoding="utf-8", newline="\n")
        self.editor.document().setModified(False)
        self.log(f"Saved · {self.current_file}")

    def _task_error(self, label: str, message: str) -> None:
        self.log(f"FAILED · {label} · {message}")

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, "log_view"):
            self.log_view.appendPlainText(f"{timestamp}  {message}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.editor.document().isModified():
            answer = QMessageBox.question(
                self,
                "Unsaved source file",
                "The current source file has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.backend.force_all_off_sync()
        event.accept()


def run() -> int:
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "art.lazying.aginti.hardware-console"
        )
    app = QApplication(sys.argv)
    app.setApplicationName("AgInTi Hardware Console")
    app.setOrganizationName("lazying.art")
    icon_path = Path(__file__).resolve().parents[1] / "assets" / "aginti-hardware-console.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = HardwareConsole()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()
