[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://lazying.art)

# AgInTi Hardware Console

**面向實驗室硬體的檔案化數位分身與控制工作臺。**

![互動式針腳圖譜](../docs/assets/hardware-console-interactive-pins.png)

它把開發板、針腳、CPU、儲存、感測器、韌體、遙測與控制意圖整合成視覺介面與結構化 JSON。介面服務實驗人員，`runtime/hardwarefs/` 則供腳本與代理使用。

## 主要功能

- 類似工作管理員的 CPU、執行內容、RAM、Flash、NAND、QSPI 與連線狀態。
- 三塊板的互動式完整針腳圖，提供懸停教學、點擊鎖定、風險配色、縮放與平移。
- AS7343 光譜、TSL2591 光強和雙 INA219 功率監測。
- STM32/ESP32 建置、燒錄、序列埠與安全燈光控制。

從 [Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases) 下載 Windows 可攜版。程式不會在啟動時自動燒錄或點燈。

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [贊助](https://chat.lazying.art/donate) · [PayPal](https://paypal.me/RongzhouChen) · [Stripe](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400)
