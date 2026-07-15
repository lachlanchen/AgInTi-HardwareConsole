[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

# AgInTi Hardware Console

**توأم رقمي قائم على الملفات ومنضدة تحكم لأجهزة المختبر.**

![خريطة الأطراف التفاعلية](../docs/assets/hardware-console-interactive-pins.png)

يجمع التطبيق اللوحات والأطراف والمعالج والذاكرة والمستشعرات والبرامج الثابتة والقياسات وأوامر التحكم في واجهة واحدة وملفات JSON منظمة. يمكن للبرامج والوكلاء استخدام `runtime/hardwarefs/` مباشرة.

## الميزات

- مدير عتاد للمعالج وسياقات التنفيذ وRAM وFlash وNAND وQSPI وحالة الاتصال.
- خريطة كاملة للأطراف مع شرح عند المرور، وتثبيت الاختيار، وألوان المخاطر، والتكبير والتحريك.
- عرض بيانات AS7343 وTSL2591 ومستشعري INA219.
- بناء وبرمجة واتصال تسلسلي وتحكم آمن في STM32 وESP32.

حمّل نسخة Windows المحمولة من [الإصدارات](https://github.com/lachlanchen/AgInTi-HardwareConsole/releases). لا يبرمج التطبيق اللوحات ولا يشغّل المصابيح تلقائياً عند البدء.

[GitHub Sponsors](https://github.com/sponsors/lachlanchen) · [تبرع](https://chat.lazying.art/donate)
