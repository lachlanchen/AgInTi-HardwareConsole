[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**Bản sao số dựa trên tệp và bàn điều khiển phần cứng phòng thí nghiệm.**

![Bản đồ chân tương tác](../docs/assets/hardware-console-interactive-pins.png)

Ứng dụng hợp nhất bo mạch, chân, CPU, bộ nhớ, cảm biến, firmware, dữ liệu đo và ý định điều khiển trong một giao diện cùng các tệp JSON có cấu trúc. `runtime/hardwarefs/` dành cho script và tác nhân tự động.

## Tính năng

- Trình quản lý phần cứng cho CPU, ngữ cảnh thực thi, RAM, Flash, NAND, QSPI và kết nối.
- Bản đồ chân đầy đủ với hướng dẫn khi rê chuột, khóa lựa chọn, màu cảnh báo, thu phóng và kéo.
- Hiển thị AS7343, TSL2591 và hai INA219.
- Biên dịch, nạp firmware, cổng nối tiếp và điều khiển STM32/ESP32 an toàn.

Tải bản Windows di động tại [Releases](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases). Ứng dụng không tự nạp firmware hoặc bật đèn khi khởi động.

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [Ủng hộ](https://chat.lazying.art/donate)
