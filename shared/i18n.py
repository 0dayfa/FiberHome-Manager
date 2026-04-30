"""Bilingual (English / Arabic) UI strings.

Technical RF terms (RSSI, RSRP, RSRQ, SINR, PCI, ARFCN, MIMO, CQI, SCC,
PCC, PLMN, IMSI, ARPU, etc.) stay in English by design — they are 3GPP
identifiers and translating them only confuses cellular engineers.
"""

LANGS = {
    "en": "English",
    "ar": "العربيه",
}

_current = "en"

STRINGS = {
    # ───── Top bar ─────
    "Main":            {"en": "Main",            "ar": "الرئيسيه"},
    "Band Select":     {"en": "Band + Cell",     "ar": "التردد + البرج"},
    "Advance":         {"en": "Advance",         "ar": "متقدم"},
    "Settings":        {"en": "Settings",        "ar": "الإعدادات"},
    "Restart Router":  {"en": "Restart Router",  "ar": "إعاده تشغيل الرواتر"},
    "Logout":          {"en": "Logout",          "ar": "خروج"},
    "Connected":       {"en": "Connected",       "ar": "متصل"},
    "Connecting...":   {"en": "Connecting…",     "ar": "جاري الاتصال…"},

    # ───── Section titles ─────
    "System Monitors":      {"en": "System Monitors",     "ar": "مراقبه النظام"},
    "General Info":         {"en": "General Info",        "ar": "معلومات عامه"},
    "Traffic Statistics":   {"en": "Traffic Statistics",  "ar": "إحصائيات البيانات"},
    "Carrier Aggregation":  {"en": "Carrier Aggregation", "ar": "تجميع الترددات"},
    "Network Info":         {"en": "Network Info",        "ar": "معلومات الشبكه"},
    "5G NR":                {"en": "5G NR",               "ar": "5G NR"},
    "4G LTE":               {"en": "4G LTE",              "ar": "4G LTE"},

    # ───── General Info chips ─────
    "Connection":          {"en": "Connection",          "ar": "الاتصال"},
    "Signal (4G+5G)":      {"en": "Signal (4G+5G)",      "ar": "الإشاره (4G+5G)"},
    "5G Status":           {"en": "5G Status",           "ar": "حاله 5G"},
    "Network Type":        {"en": "Network Type",        "ar": "نوع الشبكه"},
    "Mode · 5G Opt":       {"en": "Mode · 5G Opt",       "ar": "الوضع · 5G"},
    "Software Ver":        {"en": "Software Ver",        "ar": "إصدار البرنامج"},

    # ───── Network Info ─────
    "Numeric":             {"en": "Numeric",             "ar": "رقمي"},
    "FullName":            {"en": "FullName",            "ar": "الاسم الكامل"},
    "Total App Run Time":  {"en": "Total App Run Time",  "ar": "وقت تشغيل التطبيق"},
    "Stop":                {"en": "Stop",                "ar": "إيقاف"},
    "Start":               {"en": "Start",               "ar": "تشغيل"},

    # ───── Band Lock page ─────
    "Band Lock":           {"en": "Band Lock",           "ar": "قفل التردد"},
    "Band Lock Sub":       {"en": "Pin the modem to specific 4G LTE / 5G NR frequency bands",
                              "ar": "تثبيت المودم على ترددات 4G LTE / 5G NR محدده"},
    "ENABLED":             {"en": "ENABLED",             "ar": "مفعّل"},
    "DISABLED":            {"en": "DISABLED",            "ar": "معطّل"},
    "STATUS":              {"en": "STATUS",              "ar": "الحاله"},
    "4G LTE Currently Locked": {"en": "4G LTE Currently Locked",
                                  "ar": "4G LTE المثبّته حالياً"},
    "5G NR Currently Locked":  {"en": "5G NR Currently Locked",
                                  "ar": "5G NR المثبّته حالياً"},
    "4G LTE Bands":        {"en": "4G LTE Bands",        "ar": "ترددات 4G LTE"},
    "5G NR Bands":         {"en": "5G NR Bands",         "ar": "ترددات 5G NR"},
    "— none —":            {"en": "— none —",            "ar": "— لا يوجد —"},
    "Refresh":             {"en": "⟳  Refresh",          "ar": "⟳  تحديث"},
    "Clear All":           {"en": "✕  Clear All",        "ar": "✕  مسح الكل"},
    "Disable Lock":        {"en": "Disable Lock",        "ar": "تعطيل القفل"},
    "Apply & Enable":      {"en": "Apply & Enable",      "ar": "تطبيق وتفعيل"},
    "Modem reset note":    {"en": "ℹ  Modem will reset briefly when applying changes",
                              "ar": "ℹ  سيُعاد تشغيل المودم لحظياً عند تطبيق التغييرات"},

    # ───── Advance page ─────
    "Advanced Cellular Settings":  {"en": "Advanced Cellular Settings",
                                      "ar": "إعدادات الشبكه الخلويه المتقدمه"},
    "Adv sub": {"en": "Network mode, antenna, traffic limits, and quick toggles",
                  "ar": "وضع الشبكه، الهوائي، حدود البيانات، ومفاتيح سريعه"},
    "Loading…":  {"en": "Loading…",  "ar": "جاري التحميل…"},
    "Apply":     {"en": "Apply",     "ar": "تطبيق"},
    "Airplane Mode":   {"en": "Airplane Mode",       "ar": "وضع الطيران"},
    "AIRPLANE: ON":    {"en": "✈  AIRPLANE: ON",     "ar": "✈  الطيران: مفعّل"},
    "AIRPLANE: OFF":   {"en": "✈  AIRPLANE: OFF",    "ar": "✈  الطيران: معطّل"},
    "Airplane hint":   {"en": "Tap to toggle. Disables cellular data instantly.",
                          "ar": "اضغط للتبديل. يعطّل بيانات الشبكه الخلويه فوراً."},
    "Network Mode + 5G Option": {"en": "Network Mode + 5G Option",
                                   "ar": "وضع الشبكه + 5G"},
    "Network Mode":  {"en": "Network Mode",     "ar": "وضع الشبكه"},
    "5G Option":     {"en": "5G Option",        "ar": "وضع 5G"},
    "Roaming":       {"en": "Roaming",          "ar": "التجوال"},
    "Roaming Enabled":  {"en": "Roaming Enabled (allow non-home networks)",
                          "ar": "تفعيل التجوال (السماح للشبكات الخارجيه)"},
    "Enable Carrier Aggregation": {"en": "Enable Carrier Aggregation",
                                     "ar": "تفعيل تجميع الترددات"},
    "5G NR External Antenna":     {"en": "5G NR External Antenna",
                                     "ar": "هوائي 5G NR خارجي"},
    "Enable External Antenna":    {"en": "Enable External Antenna",
                                     "ar": "تفعيل الهوائي الخارجي"},
    "Working Band":  {"en": "Working Band",     "ar": "تردد العمل"},
    "SMS Switch":    {"en": "SMS Switch",       "ar": "خدمه SMS"},
    "Enable SMS Service": {"en": "Enable SMS Service",
                             "ar": "تفعيل خدمه SMS"},
    "VoLTE":         {"en": "VoLTE",            "ar": "VoLTE"},
    "Enable VoLTE":  {"en": "Enable VoLTE",     "ar": "تفعيل VoLTE"},
    "Traffic Control": {"en": "Traffic Control","ar": "حدود البيانات"},
    "Daily Limit":     {"en": "Daily Limit",    "ar": "الحدّ اليومي"},
    "Monthly Limit":   {"en": "Monthly Limit",  "ar": "الحدّ الشهري"},
    "Threshold:":      {"en": "Threshold:",     "ar": "الحدّ:"},

    # ───── Settings page ─────
    "Device Settings": {"en": "Device Settings","ar": "إعدادات الجهاز"},
    "Set sub": {"en": "LAN, Wi-Fi, Firewall, ACS, account and system actions",
                  "ar": "LAN، Wi-Fi، الجدار الناري، ACS، الحساب وإجراءات النظام"},
    "LAN / IPv4":  {"en": "LAN / IPv4",         "ar": "LAN / IPv4"},
    "LAN IP":      {"en": "LAN IP",             "ar": "عنوان LAN"},
    "Subnet Mask": {"en": "Subnet Mask",        "ar": "قناع الشبكه"},
    "DHCP Server": {"en": "DHCP Server",        "ar": "خادم DHCP"},
    "DHCP Start":  {"en": "DHCP Start",         "ar": "بدايه DHCP"},
    "DHCP End":    {"en": "DHCP End",           "ar": "نهايه DHCP"},
    "Lease":       {"en": "Lease",              "ar": "مده الإيجار"},
    "Wi-Fi (Primary SSIDs)": {"en": "Wi-Fi (Primary SSIDs)",
                                "ar": "Wi-Fi (الشبكات الأساسيه)"},
    "Enable SSID-1": {"en": "Enable SSID-1",    "ar": "تفعيل SSID-1"},
    "Enable SSID-2": {"en": "Enable SSID-2",    "ar": "تفعيل SSID-2"},
    "SSID-1 Name":   {"en": "SSID-1 Name",      "ar": "اسم SSID-1"},
    "SSID-2 Name":   {"en": "SSID-2 Name",      "ar": "اسم SSID-2"},
    "SSID-1 Pwd":    {"en": "SSID-1 Pwd",       "ar": "كلمه مرور SSID-1"},
    "SSID-2 Pwd":    {"en": "SSID-2 Pwd",       "ar": "كلمه مرور SSID-2"},
    "Firewall":      {"en": "Firewall",         "ar": "الجدار الناري"},
    "Firewall Level":{"en": "Firewall Level",   "ar": "مستوى الجدار الناري"},
    "ALG + UPnP":    {"en": "ALG + UPnP",       "ar": "ALG + UPnP"},
    "TR-069 / ACS":  {"en": "TR-069 / ACS",     "ar": "TR-069 / ACS"},
    "Enable CWMP / TR-069": {"en": "Enable CWMP / TR-069",
                                "ar": "تفعيل CWMP / TR-069"},
    "URL":           {"en": "URL",              "ar": "العنوان"},
    "Username":      {"en": "Username",         "ar": "اسم المستخدم"},
    "Inform Interval":{"en": "Inform Interval", "ar": "فتره الإبلاغ"},
    "Admin Password":{"en": "Admin Password",   "ar": "كلمه مرور المشرف"},
    "Current Pwd":   {"en": "Current Pwd",      "ar": "الحالي"},
    "New Pwd":       {"en": "New Pwd",          "ar": "الجديد"},
    "Confirm":       {"en": "Confirm",          "ar": "تأكيد"},
    "Change Password":{"en": "Change Password", "ar": "تغيير كلمه المرور"},
    "System Actions":{"en": "System Actions",   "ar": "إجراءات النظام"},
    "Reboot Router": {"en": "⟲  Reboot Router", "ar": "⟲  إعاده تشغيل الرواتر"},
    "Factory Reset": {"en": "⚠  Factory Reset", "ar": "⚠  إعاده ضبط المصنع"},
    "Sys warn":      {"en": "Both actions disconnect clients. Factory Reset cannot be undone.",
                        "ar": "الإجراءان يقطعان اتصال العملاء. إعاده ضبط المصنع لا يمكن التراجع عنها."},
    "Open Logs Folder": {"en": "Open Logs Folder",
                          "ar": "فتح مجلّد السجلّات"},

    # ───── Login dialog ─────
    "Login":         {"en": "Login",            "ar": "تسجيل الدخول"},
    "Sign in to":    {"en": "Sign in to manage", "ar": "سجّل الدخول لإداره"},
    "Username":      {"en": "Username",         "ar": "اسم المستخدم"},
    "Password":      {"en": "Password",         "ar": "كلمه المرور"},
    "Remember me":   {"en": "Remember me on this computer",
                        "ar": "تذكّرني على هذا الجهاز"},

    # ───── Brand ─────
    "AppName":       {"en": "FiberHome Manager — Beta",
                        "ar": "فايبر هوم مانجير — بيتا"},
    "MadeBy":        {"en": "Made by: Fahad",
                        "ar": "صنع بواسطه: Fahad"},

    # ───── IP Scan page ─────
    "IP Scan":           {"en": "IP Scan",          "ar": "فحص IP"},
    "IP Tools":          {"en": "IP Tools & Network Monitor",
                            "ar": "أدوات IP ومراقبه الشبكه"},
    "IP sub":            {"en": "Track WAN/Public IP, change IP via airplane mode, "
                                  "speed-test through Cloudflare, and pin a target IP",
                            "ar": "مراقبه IP الشبكه/العام، تغيير IP عبر وضع الطيران، "
                                  "قياس السرعه عبر Cloudflare، وتثبيت IP مستهدف"},
    "Current Network":   {"en": "Current Network",  "ar": "الشبكه الحاليه"},
    "Quick Actions":     {"en": "Quick Actions",    "ar": "إجراءات سريعه"},
    "Auto Speed Test":   {"en": "Auto Speed Test (after each IP change)",
                            "ar": "اختبار السرعه التلقائي (بعد كل تغيير IP)"},
    "IP Pinning":        {"en": "IP Pinning",       "ar": "تثبيت IP"},
    "IP Pin desc":       {"en": "Keep changing IP until target pattern matches. "
                                  "Use a prefix (10.193.89), exclude with x (1x2x3), "
                                  "or allow-list with - (10-20-30).",
                            "ar": "يستمر تغيير IP حتى يطابق النمط المستهدف. "
                                  "استخدم بادئه (10.193.89)، استبعاد بـ x (1x2x3)، "
                                  "أو قائمه مسموحه بـ - (10-20-30)."},
    "Target WAN":        {"en": "Target WAN IP",    "ar": "IP الشبكه المستهدف"},
    "Target Public":     {"en": "Target Public IP", "ar": "IP العام المستهدف"},
    "Start Pinning":     {"en": "Start Pinning",    "ar": "بدء التثبيت"},
    "Stop":              {"en": "Stop",             "ar": "إيقاف"},
    "Change IP":         {"en": "✈  Change IP",     "ar": "✈  تغيير IP"},
    "Speed Test":        {"en": "⚡  Speed Test",   "ar": "⚡  اختبار السرعه"},
    "Network Log":       {"en": "Network Log",      "ar": "سجل الشبكه"},
    "Speed Stats":       {"en": "Speed Stats Table","ar": "جدول إحصائيات السرعه"},
    "Save Log":          {"en": "💾 Save Log",      "ar": "💾 حفظ السجل"},
    "Clear Log":         {"en": "Clear",            "ar": "مسح"},
    "No logs":           {"en": "No logs yet…",     "ar": "لا توجد سجلات بعد…"},
    "WAN IP":            {"en": "WAN IP",           "ar": "IP الشبكه"},
    "Public IP":         {"en": "Public IP",        "ar": "IP العام"},
    "Status":            {"en": "Status",           "ar": "الحاله"},
    "Disconnected":      {"en": "Disconnected",     "ar": "غير متصل"},
    "Speed":             {"en": "Speed",            "ar": "السرعه"},
    "Upload":            {"en": "Upload",           "ar": "الرفع"},
    "Ping":              {"en": "Ping",             "ar": "البنج"},
    "Test count":        {"en": "Test count",       "ar": "عدد الاختبارات"},
    "IP found":          {"en": "Target IP found! Stopping.",
                            "ar": "تم العثور على IP المستهدف! إيقاف."},
    "Pinning attempts":  {"en": "attempts",         "ar": "محاولات"},
    "Searching IP":      {"en": "Searching for matching IP…",
                            "ar": "البحث عن IP مطابق…"},

    # ───── Cell Lock section ─────
    "Cell Lock":          {"en": "Cell Lock",        "ar": "قفل البرج"},
    "Cell Lock Sub":      {"en": "Pin the modem to a specific cell tower by ARFCN + PCI",
                            "ar": "تثبيت المودم على برج محدد عبر ARFCN + PCI"},
    "Locked Cells":       {"en": "Locked Cells",     "ar": "الأبراج المثبّته"},
    "Add Cell":           {"en": "Add Cell",         "ar": "إضافه برج"},
    "Tech":               {"en": "Tech",             "ar": "التقنيه"},
    "ARFCN":              {"en": "ARFCN",            "ar": "ARFCN"},
    "PCI":                {"en": "PCI",              "ar": "PCI"},
    "Action":             {"en": "Action",           "ar": "الإجراء"},
    "Delete":             {"en": "Delete",           "ar": "حذف"},
    "Mutex warn":         {"en": "Cell Lock and Band Lock cannot be enabled at the same time.",
                            "ar": "لا يمكن تفعيل قفل البرج وقفل التردد معاً في نفس الوقت."},
    "Empty cells":        {"en": "No cells locked yet — add one with the form below.",
                            "ar": "لا توجد أبراج مثبّته بعد — أضف واحداً عبر النموذج أدناه."},
    "Cell added":         {"en": "Cell added",       "ar": "تم إضافه البرج"},
    "Cell deleted":       {"en": "Cell deleted",     "ar": "تم حذف البرج"},
    "Confirm delete":     {"en": "Delete this cell from the lock list?",
                            "ar": "حذف هذا البرج من قائمه القفل؟"},

    # ───── AT Command page ─────
    "AT Command":         {"en": "AT Command",       "ar": "أوامر AT"},
    "AT title":           {"en": "AT Command Console",
                            "ar": "وحده تحكّم أوامر AT"},
    "AT sub":             {"en": "Send raw AT commands to the cellular modem and read the response",
                            "ar": "أرسل أوامر AT خام للمودم الخلوي واقرأ الاستجابه"},
    "Command":            {"en": "Command",          "ar": "الأمر"},
    "Send":               {"en": "Send",             "ar": "إرسال"},
    "Clear":              {"en": "Clear",            "ar": "مسح"},
    "Response":           {"en": "Response",         "ar": "الاستجابه"},
    "Quick commands":     {"en": "Quick Commands",   "ar": "أوامر سريعه"},
    "Sending":            {"en": "Sending…",         "ar": "جاري الإرسال…"},
    "AT placeholder":     {"en": "e.g. ATI, AT+CSQ, AT+CGMR, AT+QENG=\"servingcell\"",
                            "ar": "مثل: ATI، AT+CSQ، AT+CGMR، AT+QENG=\"servingcell\""},
}


def set_lang(code: str):
    global _current
    if code in LANGS: _current = code


def current() -> str:
    return _current


def s(key: str) -> str:
    """Translate a key. Falls back to the key itself if unknown."""
    e = STRINGS.get(key)
    if not e: return key
    return e.get(_current) or e.get("en") or key
