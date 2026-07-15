from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class AppPaths:
    app_root: Path
    dual_lamp_root: Path
    projects_root: Path
    stm32dev_root: Path


@dataclass(frozen=True)
class CommandStep:
    label: str
    argv: tuple[str, ...]
    cwd: Path


@dataclass(frozen=True)
class FirmwareProfile:
    profile_id: str
    board_id: str
    title: str
    description: str
    source_dir: Path
    build_steps: tuple[CommandStep, ...]
    flash_steps: tuple[CommandStep, ...]
    needs_port: bool = False
    safety_note: str = ""


def discover_paths() -> AppPaths:
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
    else:
        app_root = Path(__file__).resolve().parents[1]

    config_path = Path(
        os.environ.get(
            "AGINTI_HARDWARE_CONFIG",
            Path(os.environ.get("APPDATA", Path.home()))
            / "AgInTi-HardwareConsole"
            / "workspace.json",
        )
    )
    try:
        settings = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        settings = {}

    def configured(name: str, environment: str, fallback: Path) -> Path:
        value = os.environ.get(environment) or settings.get(name)
        return Path(value).expanduser().resolve() if value else fallback.resolve()

    if app_root.parent.name.lower() == "apps":
        embedded_dual_lamp = app_root.parents[1]
        default_projects = embedded_dual_lamp.parent
    else:
        embedded_dual_lamp = app_root.parent / "DualLampHI"
        default_projects = app_root.parent

    projects_root = configured("projects_root", "AGINTI_PROJECTS_ROOT", default_projects)
    dual_lamp_root = configured(
        "dual_lamp_root",
        "DUALLAMPHI_ROOT",
        embedded_dual_lamp if embedded_dual_lamp.exists() else projects_root / "DualLampHI",
    )
    stm32dev_root = configured("stm32dev_root", "STM32DEV_ROOT", projects_root / "stm32dev")
    return AppPaths(
        app_root=app_root,
        dual_lamp_root=dual_lamp_root,
        projects_root=projects_root,
        stm32dev_root=stm32dev_root,
    )


def firmware_profiles(paths: AppPaths) -> Mapping[str, FirmwareProfile]:
    h7_source = paths.stm32dev_root / "firmware" / "stm32_sensor_head_lcd"
    h7_elf = h7_source / "build" / "stm32_sensor_head_lcd.elf"
    f103_static = paths.stm32dev_root / "firmware" / "stm32f103_sk6812_static_led1"
    f103_ramp = paths.stm32dev_root / "firmware" / "stm32f103_addressable_led_ramp"
    f103_cycle = paths.stm32dev_root / "firmware" / "stm32f103_sk6812_rgbw"
    esp32_tsl = paths.stm32dev_root / "firmware" / "esp32_tsl2591_reader"

    return {
        "h7_sensor": FirmwareProfile(
            profile_id="h7_sensor",
            board_id="h7",
            title="H7 Sensor Head",
            description="LCD + AS7343 + TSL2591 + dual INA219 monitor + lamp PWM",
            source_dir=h7_source,
            build_steps=(
                CommandStep(
                    "Build H7 sensor firmware",
                    ("make", "-C", str(h7_source)),
                    paths.stm32dev_root,
                ),
            ),
            flash_steps=(
                CommandStep(
                    "Flash H7 through onboard ST-Link",
                    (
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
                        f"program {h7_elf} verify reset exit",
                    ),
                    paths.stm32dev_root,
                ),
            ),
            safety_note="Flashing restarts measurement and forces the lamp outputs through boot state.",
        ),
        "f103_static": FirmwareProfile(
            profile_id="f103_static",
            board_id="f103",
            title="F103 SK6812 Static",
            description="Verified LED1 red + LED2 green static diagnostic",
            source_dir=f103_static,
            build_steps=(CommandStep("Build F103 static image", ("make",), f103_static),),
            flash_steps=(CommandStep("Flash F103 static image", ("make", "flash"), f103_static),),
        ),
        "f103_ramp": FirmwareProfile(
            profile_id="f103_ramp",
            board_id="f103",
            title="F103 Addressable LED Ramp",
            description="SK6812/WS2812B-aware 0..255..0 range test",
            source_dir=f103_ramp,
            build_steps=(CommandStep("Build F103 range image", ("make",), f103_ramp),),
            flash_steps=(CommandStep("Flash F103 range image", ("make", "flash"), f103_ramp),),
        ),
        "f103_cycle": FirmwareProfile(
            profile_id="f103_cycle",
            board_id="f103",
            title="F103 SK6812 Color Cycle",
            description="Preserved two-pixel RGBW sequence firmware",
            source_dir=f103_cycle,
            build_steps=(CommandStep("Build F103 color cycle", ("make",), f103_cycle),),
            flash_steps=(CommandStep("Flash F103 color cycle", ("make", "flash"), f103_cycle),),
        ),
        "esp32_tsl": FirmwareProfile(
            profile_id="esp32_tsl",
            board_id="esp32",
            title="ESP32-S3 TSL2591 Reader",
            description="Waveshare ESP32-S3: IO9=SCL, IO8=SDA, 115200 baud CSV",
            source_dir=esp32_tsl,
            build_steps=(
                CommandStep(
                    "Compile ESP32-S3 reader",
                    (
                        "arduino-cli",
                        "compile",
                        "--fqbn",
                        "esp32:esp32:esp32s3",
                        str(esp32_tsl),
                    ),
                    paths.stm32dev_root,
                ),
            ),
            flash_steps=(
                CommandStep(
                    "Upload ESP32-S3 reader",
                    (
                        "arduino-cli",
                        "upload",
                        "--fqbn",
                        "esp32:esp32:esp32s3",
                        "-p",
                        "{port}",
                        str(esp32_tsl),
                    ),
                    paths.stm32dev_root,
                ),
            ),
            needs_port=True,
            safety_note="The ESP32 profile remains offline until a serial port is selected.",
        ),
    }


BOARD_COPY = {
    "h7": {
        "name": "STM32H743 Sensor Head",
        "subtitle": "Measurement + LCD + dual-lamp PWM",
        "usb": "ST-Link/V2-1 0483:374B",
        "accent": "#22B8A7",
    },
    "f103": {
        "name": "STM32F103 Pixel Controller",
        "subtitle": "SK6812 / WS2812B waveform engine",
        "usb": "External ST-Link 0483:3748",
        "accent": "#E6A23C",
    },
    "esp32": {
        "name": "ESP32-S3 N8R8",
        "subtitle": "Portable sensor endpoint (optional)",
        "usb": "Serial / native USB",
        "accent": "#55A7FF",
    },
}
