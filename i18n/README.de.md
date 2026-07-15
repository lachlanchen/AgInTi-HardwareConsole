[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**Ein dateibasiertes digitales Labor-Hardware-Abbild und Steuerungs-Workbench.**

![Interaktiver Pin-Atlas](../docs/assets/hardware-console-interactive-pins.png)

Boards, Pins, CPU, Speicher, Sensoren, Firmware, Telemetrie und Steuerungsabsichten werden in einer Oberfläche und strukturierten JSON-Dateien zusammengeführt. `runtime/hardwarefs/` kann von Skripten und Agenten genutzt werden.

## Funktionen

- Hardware-Task-Manager für CPU, Ausführungskontexte, RAM, Flash, NAND, QSPI und Verbindungen.
- Vollständiger Pin-Atlas mit Hover-Hilfe, Auswahl, Risikofarben, Zoom und Verschieben.
- Visualisierung für AS7343, TSL2591 und zwei INA219.
- Build, Flash, Seriell und sichere Steuerung für STM32/ESP32.

Die portable Windows-Version ist unter [Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases) verfügbar. Beim Start werden weder Firmware geschrieben noch Lampen eingeschaltet.

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [Spenden](https://chat.lazying.art/donate)
