<div align="center">

# FiberHome Manager — Beta

**A modern desktop control panel for the FiberHome LG6851F 5G router.**
*Replaces the slow web UI at `192.168.8.1` with a fast, real-time native app.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt-5.15%2B-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-Personal_use-orange.svg)](#license)

![Main dashboard](docs/screenshots/main.png)

</div>

---

## 🌍 العربيه

### نظره عامه

**FiberHome Manager** تطبيق سطح مكتب لإداره ومراقبه راوتر **FiberHome LG6851F**
(موديم 5G من Quectel RG620T). يستبدل صفحه الرواتر الويب البطيئه بواجهه أصليه
سريعه — قراءات لحظيه للإشاره، تحكم كامل بالترددات، اختبار سرعه، ومراقبه IP.

### المميزات

| المنطقه | المحتوى |
|---|---|
| **Main** | قراءات لحظيه (RSRP/RSRQ/SINR/RSSI) للـ 4G + 5G · رسوم بيانيه ملوّنه · جدول CA · إحصائيات بيانات · حاله النظام |
| **Band + Cell** | قفل ترددات LTE/NR متعدّد · قفل برج محدّد عبر ARFCN+PCI · منع تعارض تلقائي |
| **Advance** | وضع طيران لحظي · Network Mode + 5G Option · Roaming · Carrier Aggregation · هوائي 5G NR خارجي · SMS · VoLTE · حدود البيانات اليومي/الشهري |
| **Settings** | LAN/IPv4 · Wi-Fi (SSID-1/2) · Firewall · ALG + UPnP · TR-069/ACS · تغيير كلمه المشرف · Reboot/Factory Reset |
| **IP Scan** | مراقبه WAN/Public IP لحظياً · تغيير IP عبر airplane mode · Speed Test مخفي عبر Fast.com · IP Pinning بأنماط · جدول إحصائيات |
| **AT Command** | إرسال أوامر AT خام للموديم + 11 أمر جاهز (ATI, AT+CSQ, AT+QENG, ...) |

**ميزات إضافيه**:
- 🌗 ثلاثه ثيمات: Light · Dark (Tokyo Night) · Aurora — تبديل فوري
- 🌐 لغتان: English / العربيه — مع RTL تلقائي
- 🔐 حفظ بيانات الدخول (تسجيل دخول تلقائي)
- 📋 سجلّات تشغيل مدوّره (لتشخيص المشاكل)
- ✅ فحص نظام أوّلي قبل التشغيل
- 📊 صفحه Main أفقيه احترافيه — تتسع على شاشه 720p

### المتطلبات

| المتطلّب | للمستخدم النهائي | للمطوّر/البناء |
|---|---|---|
| Windows 10 / 11 (x64) | ✅ | ✅ |
| Microsoft Visual C++ 2015–2022 Redistributable | ✅ (الـ Preflight يحمّله تلقائياً) | ✅ |
| اتصال LAN/Wi-Fi مع الرواتر | ✅ | — |
| Python 3.10+ | ❌ غير مطلوب | ✅ |
| PyQt5 / PyQtWebEngine / websocket-client | ❌ مدمج في الـ exe | يثبّتها `build.bat` |
| متصفّح (Edge/Chrome) | ❌ غير مطلوب — Qt يحمل Chromium | — |

### البناء بضغطه واحده

```cmd
build.bat
```

السكربت يفحص بايثون + pip + الملفات + المكتبات + يبني الـ exe — كل ذلك تلقائياً.

النتيجه في `dist\FiberHome Manager - Beta\` — انسخ المجلّد كاملاً للتوزيع (~266 MB لأنه يحتوي على Chromium مدمج).

### السكربت اليدوي (بديل)

```cmd
pip install -r requirements.txt
pip install pyinstaller
pyinstaller FiberHomeManager.spec --noconfirm
```

---

## 🌐 English

### Overview

**FiberHome Manager** is a desktop control panel for the **FiberHome LG6851F** 5G router
(Quectel RG620T modem). It replaces the slow `192.168.8.1` web UI with a fast,
native experience — real-time signal readings, full band/cell control,
speed tests, and IP scanning.

### Features

| Page | Content |
|---|---|
| **Main** | Live RSRP/RSRQ/SINR/RSSI for 4G + 5G · color-zone charts · CA table · traffic stats · system gauges |
| **Band + Cell** | Multi-band LTE/NR lock · single-cell lock by ARFCN+PCI · automatic mutual-exclusion enforcement |
| **Advance** | Airplane toggle · Network Mode + 5G Option · Roaming · Carrier Aggregation · 5G NR external antenna · SMS · VoLTE · daily/monthly traffic limits |
| **Settings** | LAN/IPv4 · Wi-Fi (SSID-1/2 + passwords) · Firewall · ALG + UPnP · TR-069/ACS · admin password · Reboot/Factory Reset |
| **IP Scan** | Live WAN/Public IP monitor · IP changer via airplane mode · hidden Fast.com speed test · pattern-based IP pinning · sortable speed-stats table |
| **AT Command** | Raw AT command console + 11 presets (ATI, AT+CSQ, AT+QENG, ...) |

<div align="center">

![IP Scan with hidden Fast.com speed test](docs/screenshots/speed-test.png)

*IP Scan tab — live IP monitor + Fast.com speed test rendered in a hidden Chromium pane.*

</div>

**Extras**:
- 🌗 Three themes: Light · Dark (Tokyo Night) · Aurora — switches live
- 🌐 Bilingual: English / Arabic — automatic RTL
- 🔐 Saved-credentials auto-login
- 📋 Rotating diagnostic logs
- ✅ First-run system preflight (downloads VC++ runtime if missing)
- 📊 Horizontal main dashboard — fits 720p comfortably

### Requirements

| Requirement | End user | Developer |
|---|---|---|
| Windows 10 / 11 (x64) | ✅ | ✅ |
| Microsoft Visual C++ 2015–2022 Redistributable | ✅ (preflight installs if missing) | ✅ |
| Network connection to the router | ✅ | — |
| Python 3.10+ | ❌ not needed | ✅ |
| PyQt5 / PyQtWebEngine / websocket-client | ❌ bundled into the EXE | installed by `build.bat` |
| Edge / Chrome browser | ❌ not needed (Qt ships its own Chromium) | — |

### One-Click Build

```cmd
build.bat
```

The script checks Python, pip, project files and dependencies, only installs
what's missing, then runs PyInstaller. Output lands in
`dist\FiberHome Manager - Beta\`.

### Manual Build

```cmd
pip install -r requirements.txt
pip install pyinstaller
pyinstaller FiberHomeManager.spec --noconfirm
```

### Project Layout

```
.
├─ README.md                    ← this file
├─ requirements.txt             ← Python deps for the build machine
├─ build.bat                    ← smart one-click build script
├─ FiberHomeManager.spec        ← PyInstaller spec
│
├─ api_client.py                ← WebSocket bridge to the router
├─ router_api.py                ← high-level router API helpers
├─ workers.py                   ← QThread polling workers
├─ ws_client.py                 ← raw WebSocket transport
│
├─ shared/
│   ├─ data_hub.py              ← central state + run_design launcher
│   ├─ themes.py                ← Light / Dark / Aurora palettes
│   ├─ i18n.py                  ← EN/AR translation tables
│   ├─ auth_store.py            ← saved credentials + prefs (~/.fiberguard)
│   ├─ login_view.py            ← login dialog
│   ├─ preflight.py             ← system checks (VC++/router/internet)
│   ├─ preflight_view.py        ← preflight Qt dialog
│   ├─ debug_log.py             ← rotating logger
│   ├─ network_tools.py         ← public-IP fetcher
│   ├─ ip_workers.py            ← IP-scan QThreads
│   ├─ fast_speed_test.py       ← hidden Fast.com scraper (QWebEngineView)
│   └─ assets/
│       ├─ logo.svg
│       └─ logo_icon.svg
│
├─ widgets/                     ← live-chart, gauges, info grids
├─ designs/d01_engineering/
│   ├─ main.py                  ← the Engineering Console window
│   ├─ usage_gauge.py
│   ├─ zone_chart.py
│   └─ ...
│
└─ _archive/                    ← old prototypes + research scripts (excluded from build)
```

### Logs

Every session writes to `%USERPROFILE%\.fiberguard\logs\app.log` (rotating: 5×1 MB).
The **📋 Open Logs Folder** button under *Settings → System Actions* opens it.
Attach the file to bug reports — it captures every login attempt, view switch,
API error, and unhandled exception.

### Disclaimer

Personal / educational use. Not affiliated with FiberHome or Quectel.

---

<div align="center">

**Made by Fahad** · [routers.world](https://routers.world)

</div>
