[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**研究室ハードウェアのための、ファイルベースのデジタルツイン兼制御ワークベンチです。**

![インタラクティブなピンアトラス](../docs/assets/hardware-console-interactive-pins.png)

ボード、全ピン、CPU、ストレージ、センサー、ファームウェア、テレメトリ、制御意図を、GUI と構造化 JSON に統合します。`runtime/hardwarefs/` はスクリプトやエージェントからも利用できます。

## 主な機能

- CPU、実行コンテキスト、RAM、Flash、NAND、QSPI、接続状態を表示するハードウェアタスクマネージャー。
- ホバー解説、クリック固定、危険度表示、ズーム、パンに対応した完全なピンアトラス。
- AS7343、TSL2591、デュアル INA219 の可視化。
- STM32/ESP32 のビルド、書き込み、シリアル、安全な照明制御。

[Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases) から Windows ポータブル版を取得できます。起動時に自動書き込みや点灯は行いません。

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [寄付](https://chat.lazying.art/donate)
