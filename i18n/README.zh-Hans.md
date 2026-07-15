[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**面向实验室硬件的文件化数字孪生与控制工作台。**

![交互式针脚图谱](../docs/assets/hardware-console-interactive-pins.png)

它把开发板、全部针脚、CPU、存储、传感器、固件、遥测与控制意图统一成可视界面和结构化 JSON 文件。界面服务于实验人员，`runtime/hardwarefs/` 服务于脚本和智能体。

## 功能

- 类似任务管理器的 CPU、执行上下文、RAM、Flash、NAND、QSPI 和连接状态。
- 三块板的交互式全针脚图，支持悬停教学、单击锁定、风险着色、缩放和平移。
- AS7343 光谱、TSL2591 强度和双 INA219 功率监测。
- STM32/ESP32 构建、烧录、串口和安全灯光控制。
- 零硬件时仍可离线查看资料，不伪造在线状态。

## Windows 启动

从 [Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases) 下载便携版，解压后运行 `AgInTi-HardwareConsole.exe`。源码方式请参考[英文主页](../README.md)。

## 安全

程序启动时不会自动烧录或点灯。灯光默认限时运行，关闭程序会请求全部关闭。GPIO 只输出逻辑信号，灯和电机必须使用外部电源与驱动器，并与控制器共信号地。

## 支持

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [捐赠](https://chat.lazying.art/donate) · [PayPal](https://paypal.me/RongzhouChen) · [Stripe](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400)
