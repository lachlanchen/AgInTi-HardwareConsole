from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Iterable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .config import AppPaths, CommandStep, FirmwareProfile
from .digital_twin import HardwareFileSystem


CREATE_NO_WINDOW = 0x08000000
H7_STLINK_LOCK = threading.Lock()


class WorkerSignals(QObject):
    line = Signal(str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, function: Callable[[Callable[[str], None]], Any]) -> None:
        super().__init__()
        self.function = function
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.function(self.signals.line.emit)
        except Exception as exc:  # Hardware errors must reach the GUI, not kill it.
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


def run_command(
    argv: Iterable[str], cwd: Path, emit: Callable[[str], None], timeout: float | None = None
) -> str:
    rendered = [str(item) for item in argv]
    emit(f"$ {' '.join(rendered)}")
    process = subprocess.Popen(
        rendered,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    lines: list[str] = []
    assert process.stdout is not None
    try:
        for line in process.stdout:
            clean = line.rstrip()
            lines.append(clean)
            emit(clean)
        return_code = process.wait(timeout=timeout)
    except Exception:
        process.kill()
        process.wait()
        raise
    if return_code != 0:
        raise RuntimeError(f"Command failed with exit code {return_code}: {' '.join(rendered)}")
    return "\n".join(lines)


def run_steps(
    steps: Iterable[CommandStep], values: dict[str, str], emit: Callable[[str], None]
) -> dict[str, Any]:
    completed: list[str] = []
    for step in steps:
        emit(f"\n[{step.label}]")
        argv = tuple(part.format(**values) for part in step.argv)
        run_command(argv, step.cwd, emit)
        completed.append(step.label)
    return {"completed": completed}


def probe_devices(_: Callable[[str], None]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "h7": {"online": False, "detail": "Not detected"},
        "f103": {"online": False, "detail": "Not detected"},
        "esp32": {"online": False, "detail": "Not detected"},
        "ports": [],
        "tools": {
            name: bool(shutil.which(name))
            for name in ("openocd", "arm-none-eabi-gcc", "make", "arduino-cli")
        },
    }

    if shutil.which("powershell") or shutil.which("powershell.exe"):
        command = (
            "Get-PnpDevice -PresentOnly | Select-Object FriendlyName,InstanceId "
            "| ConvertTo-Json -Compress"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
        haystack = (result.stdout + result.stderr).upper()
        if "VID_0483&PID_374B" in haystack:
            state["h7"] = {"online": True, "detail": "Onboard ST-Link/V2-1"}
        if "VID_0483&PID_3748" in haystack:
            state["f103"] = {"online": True, "detail": "External ST-Link V2"}
        if any(token in haystack for token in ("VID_303A", "CP210", "CH340", "ESP32")):
            state["esp32"] = {"online": True, "detail": "USB serial device found"}

    try:
        from serial.tools import list_ports

        ports = []
        for port in list_ports.comports():
            ports.append(
                {
                    "device": port.device,
                    "description": port.description or "Serial device",
                    "vid": port.vid,
                    "pid": port.pid,
                }
            )
        state["ports"] = ports
    except Exception:
        pass
    return state


SYMBOL_SIZES = {
    "as_sample_count": 4,
    "lamp_pwm1": 2,
    "lamp_pwm2": 2,
    "last_as": 36,
    "last_bus1_mV": 2,
    "last_bus2_mV": 2,
    "last_current1_mA": 2,
    "last_current2_mA": 2,
    "last_power1_mW": 4,
    "last_power2_mW": 4,
    "last_status2": 1,
    "last_tsl0": 2,
    "last_tsl1": 2,
    "last_tsl0_norm": 4,
    "last_tsl_visible_norm": 4,
    "ok_as7343": 1,
    "ok_monitor1": 1,
    "ok_monitor2": 1,
    "ok_tsl": 1,
    "seq": 4,
    "tsl_sample_count": 4,
}


def parse_symbols(elf: Path) -> dict[str, int]:
    result = subprocess.run(
        ["arm-none-eabi-nm", "-n", str(elf)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        creationflags=CREATE_NO_WINDOW,
        check=True,
    )
    symbols: dict[str, int] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] in SYMBOL_SIZES:
            symbols[parts[-1]] = int(parts[0], 16)
    missing = set(SYMBOL_SIZES).difference(symbols)
    if missing:
        raise RuntimeError(f"H7 ELF is missing live symbols: {', '.join(sorted(missing))}")
    return symbols


def parse_mdb(output: str, start: int, count: int) -> bytearray:
    data = bytearray(count)
    seen = 0
    for line in output.splitlines():
        match = re.match(r"\s*0x([0-9a-fA-F]+):\s*(.*)$", line)
        if not match:
            continue
        address = int(match.group(1), 16)
        tokens = re.findall(r"\b[0-9a-fA-F]{2}\b", match.group(2))
        for offset, token in enumerate(tokens):
            index = address + offset - start
            if 0 <= index < count:
                data[index] = int(token, 16)
                seen += 1
    if seen < count:
        raise RuntimeError(f"OpenOCD returned only {seen}/{count} requested RAM bytes")
    return data


def h7_snapshot(paths: AppPaths, emit: Callable[[str], None]) -> dict[str, Any]:
    elf = paths.stm32dev_root / "firmware" / "stm32_sensor_head_lcd" / "build" / "stm32_sensor_head_lcd.elf"
    if not elf.exists():
        raise RuntimeError(f"Build the H7 firmware first; ELF not found: {elf}")
    symbols = parse_symbols(elf)
    start = min(symbols.values()) & ~0x0F
    end = max(symbols[name] + SYMBOL_SIZES[name] for name in symbols)
    count = ((end - start + 15) // 16) * 16

    command = (
        "openocd",
        "-f",
        "interface/stlink.cfg",
        "-c",
        "hla_vid_pid 0x0483 0x374B",
        "-f",
        "target/stm32h7x.cfg",
        "-c",
        "adapter speed 1000",
        "-c",
        "init; halt",
        "-c",
        f"mdb 0x{start:08x} {count}",
        "-c",
        "resume; shutdown",
    )
    with H7_STLINK_LOCK:
        result = subprocess.run(
            command,
            cwd=str(paths.stm32dev_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        emit(output.strip())
        raise RuntimeError("Unable to read H7 sensor RAM through ST-Link")
    memory = parse_mdb(output, start, count)

    def raw(name: str) -> bytes:
        index = symbols[name] - start
        return bytes(memory[index : index + SYMBOL_SIZES[name]])

    def u8(name: str) -> int:
        return raw(name)[0]

    def u16(name: str) -> int:
        return struct.unpack("<H", raw(name))[0]

    def u32(name: str) -> int:
        return struct.unpack("<I", raw(name))[0]

    spectrum = list(struct.unpack("<18H", raw("last_as")))
    full = u16("last_tsl0")
    infrared = u16("last_tsl1")
    return {
        "devices": {
            "as7343": bool(u8("ok_as7343")),
            "tsl2591": bool(u8("ok_tsl")),
            "monitor1": bool(u8("ok_monitor1")),
            "monitor2": bool(u8("ok_monitor2")),
        },
        "as7343": {
            "channels": spectrum,
            "samples": u32("as_sample_count"),
            "status2": u8("last_status2"),
        },
        "tsl2591": {
            "full": full,
            "infrared": infrared,
            "visible": max(0, full - infrared),
            "full_normalized": u32("last_tsl0_norm"),
            "visible_normalized": u32("last_tsl_visible_norm"),
            "samples": u32("tsl_sample_count"),
        },
        "monitor": {
            "lamp1": {
                "bus_mV": u16("last_bus1_mV"),
                "current_mA": u16("last_current1_mA"),
                "power_mW": u32("last_power1_mW"),
            },
            "lamp2": {
                "bus_mV": u16("last_bus2_mV"),
                "current_mA": u16("last_current2_mA"),
                "power_mW": u32("last_power2_mW"),
            },
        },
        "pwm": {"lamp1": u16("lamp_pwm1"), "lamp2": u16("lamp_pwm2")},
        "seq": u32("seq"),
    }


class HardwareBackend(QObject):
    logLine = Signal(str)
    devicesChanged = Signal(dict)
    snapshotChanged = Signal(dict)
    taskStarted = Signal(str)
    taskFinished = Signal(str, bool)
    taskError = Signal(str, str)
    twinChanged = Signal(dict)

    def __init__(self, paths: AppPaths, profiles: dict[str, FirmwareProfile]) -> None:
        super().__init__()
        self.paths = paths
        self.profiles = profiles
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(3)
        self.snapshot_busy = False
        self.twin = HardwareFileSystem(
            paths.app_root / "device_profiles",
            paths.app_root / "runtime" / "hardwarefs",
        )

    def _submit(
        self,
        label: str,
        function: Callable[[Callable[[str], None]], Any],
        on_result: Callable[[Any], None] | None = None,
        intent_id: str | None = None,
    ) -> None:
        worker = FunctionWorker(function)
        worker.signals.line.connect(self.logLine)
        worker.signals.error.connect(
            lambda message: self._worker_failed(label, message, intent_id)
        )
        worker.signals.result.connect(
            lambda result: self._worker_succeeded(label, result, on_result, intent_id)
        )
        self.taskStarted.emit(label)
        self.pool.start(worker)

    def _worker_succeeded(
        self,
        label: str,
        result: Any,
        on_result: Callable[[Any], None] | None,
        intent_id: str | None,
    ) -> None:
        if on_result is not None:
            on_result(result)
        if intent_id is not None:
            self.twin.finish_intent(intent_id, "completed", result)
            self.twinChanged.emit(self.twin.model())
        self.taskFinished.emit(label, True)

    def _worker_failed(self, label: str, message: str, intent_id: str | None) -> None:
        if intent_id is not None:
            self.twin.finish_intent(intent_id, "failed", {"error": message})
            self.twinChanged.emit(self.twin.model())
        self._on_error(label, message)
        self.taskFinished.emit(label, False)

    def _on_error(self, label: str, message: str) -> None:
        self.logLine.emit(f"ERROR [{label}] {message}")
        self.taskError.emit(label, message)

    def refresh_devices(self) -> None:
        def accepted(state: dict[str, Any]) -> None:
            self.twin.update_connectivity(state)
            self.devicesChanged.emit(state)
            self.twinChanged.emit(self.twin.model())

        self._submit("Device discovery", probe_devices, accepted)

    def refresh_twin(self) -> None:
        self.twinChanged.emit(self.twin.model())

    def run_profile(self, profile_id: str, action: str, port: str = "") -> None:
        profile = self.profiles[profile_id]
        if profile.needs_port and not port:
            self._on_error(profile.title, "Select a serial port first")
            return
        if action == "build":
            steps = profile.build_steps
        elif action == "flash":
            steps = profile.flash_steps
        else:
            steps = profile.build_steps + profile.flash_steps
        intent_id = self.twin.create_intent(
            profile.board_id,
            f"firmware.{action}",
            {"profile_id": profile_id, "port": port or None},
        )
        self.twinChanged.emit(self.twin.model())
        self._submit(
            f"{profile.title}: {action}",
            lambda emit: run_steps(steps, {"port": port}, emit),
            intent_id=intent_id,
        )

    def lamp(self, command: str, duty: int, seconds: float, hold: bool = False) -> None:
        script = self.paths.stm32dev_root / "scripts" / "stm32_lamp_control.py"
        intent_id = self.twin.create_intent(
            "h7",
            f"lamp.{command}",
            {"duty": duty, "seconds": seconds, "hold": hold},
        )
        self.twinChanged.emit(self.twin.model())

        def operation(emit: Callable[[str], None]) -> dict[str, Any]:
            argv = ["python", str(script), command]
            if command not in ("off", "status"):
                argv += ["--duty", str(duty), "--seconds", str(seconds)]
                if hold:
                    argv.append("--hold")
            with H7_STLINK_LOCK:
                run_command(argv, self.paths.stm32dev_root, emit, timeout=max(20.0, seconds + 15.0))
            return {"command": command}

        self._submit(f"Lamp command: {command}", operation, intent_id=intent_id)

    def read_snapshot(self) -> None:
        if self.snapshot_busy:
            return
        self.snapshot_busy = True
        worker = FunctionWorker(lambda emit: h7_snapshot(self.paths, emit))
        worker.signals.line.connect(self.logLine)
        worker.signals.result.connect(self._snapshot_accepted)
        worker.signals.error.connect(lambda message: self._on_error("H7 snapshot", message))
        worker.signals.finished.connect(self._snapshot_finished)
        self.pool.start(worker)

    def _snapshot_finished(self) -> None:
        self.snapshot_busy = False

    def _snapshot_accepted(self, snapshot: dict[str, Any]) -> None:
        self.twin.update_h7_snapshot(snapshot)
        self.snapshotChanged.emit(snapshot)
        self.twinChanged.emit(self.twin.model())

    def force_all_off_sync(self) -> None:
        script = self.paths.stm32dev_root / "scripts" / "stm32_lamp_control.py"
        if not script.exists() or not shutil.which("openocd"):
            return
        try:
            with H7_STLINK_LOCK:
                subprocess.run(
                    ["python", str(script), "off"],
                    cwd=str(self.paths.stm32dev_root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=12,
                    creationflags=CREATE_NO_WINDOW,
                    check=False,
                )
        except Exception:
            pass
