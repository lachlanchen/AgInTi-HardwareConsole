[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**실험실 하드웨어를 위한 파일 기반 디지털 트윈 및 제어 워크벤치입니다.**

![대화형 핀 아틀라스](../docs/assets/hardware-console-interactive-pins.png)

보드, 모든 핀, CPU, 저장장치, 센서, 펌웨어, 텔레메트리와 제어 의도를 하나의 GUI와 구조화된 JSON 파일로 통합합니다. `runtime/hardwarefs/`는 스크립트와 에이전트도 사용할 수 있습니다.

## 주요 기능

- CPU, 실행 컨텍스트, RAM, Flash, NAND, QSPI 및 연결 상태를 보여 주는 하드웨어 작업 관리자.
- 호버 설명, 클릭 고정, 위험 색상, 확대/축소 및 이동을 지원하는 전체 핀 지도.
- AS7343, TSL2591 및 듀얼 INA219 시각화.
- STM32/ESP32 빌드, 플래시, 시리얼 및 안전한 조명 제어.

[Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases)에서 Windows 포터블 버전을 받을 수 있습니다. 시작 시 자동 플래시나 램프 점등을 하지 않습니다.

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [후원](https://chat.lazying.art/donate)
