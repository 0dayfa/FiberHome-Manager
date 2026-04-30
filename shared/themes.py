"""3 themes for FiberGuard — Light (default), Dark (Tokyo Night), Aurora.

Every screen pulls colors from a single dict so swapping themes
re-styles the whole app without touching individual widgets.
"""

THEMES = {
    "light": {
        # canvas
        "bg":         "#F0F2F5",
        "bg_alt":     "#E8E8E8",
        "card":       "#FFFFFF",
        "card_alt":   "#F8F8F8",
        "border":     "#D0D0D0",
        "border_lt":  "#E0E4E8",
        # text
        "fg":         "#222222",
        "fg_dim":     "#666666",
        "fg_mute":    "#90A4AE",
        # accents
        "accent":     "#0D47A1",
        "accent_2":   "#1565C0",
        "accent_bg":  "#E3F2FD",
        # input
        "input_bg":   "#FFFFFF",
        "input_br":   "#B0B0B0",
        # status
        "ok":         "#10B981",
        "ok_bg":      "#90EE90",
        "warn":       "#F59E0B",
        "warn_bg":    "#FFEB99",
        "err":        "#EF4444",
        "err_bg":     "#FF8080",
        "info_bg":    "#7FBFFF",
        # topbar
        "topbar":     "#FFFFFF",
        "topbtn":     "#FCFCFC",
        "topbtn_hov": "#E0E0E0",
        # chart
        "chart_bg":   "#FFFFFF",
        "chart_grid": "#E0E0E0",
        "chart_axis": "#666666",
    },
    "dark": {  # Tokyo Night
        "bg":         "#1A1B26",
        "bg_alt":     "#16161E",
        "card":       "#24283B",
        "card_alt":   "#1F2335",
        "border":     "#414868",
        "border_lt":  "#2F334D",
        "fg":         "#C0CAF5",
        "fg_dim":     "#9AA5CE",
        "fg_mute":    "#565F89",
        "accent":     "#7AA2F7",
        "accent_2":   "#9ECE6A",
        "accent_bg":  "#2A3045",
        "input_bg":   "#1F2335",
        "input_br":   "#414868",
        "ok":         "#9ECE6A",
        "ok_bg":      "#2A3F2A",
        "warn":       "#E0AF68",
        "warn_bg":    "#3F3520",
        "err":        "#F7768E",
        "err_bg":     "#3F2A30",
        "info_bg":    "#7AA2F7",
        "topbar":     "#16161E",
        "topbtn":     "#1F2335",
        "topbtn_hov": "#2F334D",
        "chart_bg":   "#1A1B26",
        "chart_grid": "#2F334D",
        "chart_axis": "#9AA5CE",
    },
    "aurora": {  # Deep purple + teal + pink — modern aesthetic
        "bg":         "#15131F",
        "bg_alt":     "#0F0E1A",
        "card":       "#1E1A2E",
        "card_alt":   "#231E36",
        "border":     "#3A2F52",
        "border_lt":  "#2A2340",
        "fg":         "#E6E1F0",
        "fg_dim":     "#B8AED4",
        "fg_mute":    "#7B6F9A",
        "accent":     "#06B6D4",   # teal
        "accent_2":   "#EC4899",   # pink
        "accent_bg":  "#1A2A38",
        "input_bg":   "#1E1A2E",
        "input_br":   "#3A2F52",
        "ok":         "#10F4B1",
        "ok_bg":      "#0F2E26",
        "warn":       "#FBBF24",
        "warn_bg":    "#3F2E14",
        "err":        "#F472B6",
        "err_bg":     "#3F1F30",
        "info_bg":    "#06B6D4",
        "topbar":     "#0F0E1A",
        "topbtn":     "#1E1A2E",
        "topbtn_hov": "#2A2340",
        "chart_bg":   "#15131F",
        "chart_grid": "#2A2340",
        "chart_axis": "#B8AED4",
    },
}


_current = "light"


def set_theme(name: str):
    global _current
    if name in THEMES: _current = name


def current() -> str:
    return _current


def t(key: str) -> str:
    """Look up a color from the active theme. Falls back to '#888'."""
    return THEMES.get(_current, THEMES["light"]).get(key, "#888")


def apply_palette(app, theme: str | None = None):
    """The Fusion style ignores QSS background for QLineEdit/QComboBox/QSpinBox
    and paints those widgets from the QPalette instead — so themes only stick
    if we patch the palette as well as the stylesheet."""
    from PyQt5.QtGui import QPalette, QColor
    th = THEMES.get(theme or _current, THEMES["light"])
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(th['bg']))
    p.setColor(QPalette.WindowText,      QColor(th['fg']))
    p.setColor(QPalette.Base,            QColor(th['input_bg']))
    p.setColor(QPalette.AlternateBase,   QColor(th['card_alt']))
    p.setColor(QPalette.ToolTipBase,     QColor(th['card']))
    p.setColor(QPalette.ToolTipText,     QColor(th['fg']))
    p.setColor(QPalette.Text,            QColor(th['fg']))
    p.setColor(QPalette.PlaceholderText, QColor(th['fg_mute']))
    p.setColor(QPalette.Button,          QColor(th['topbtn']))
    p.setColor(QPalette.ButtonText,      QColor(th['fg']))
    p.setColor(QPalette.BrightText,      QColor("#FFFFFF"))
    p.setColor(QPalette.Highlight,       QColor(th['accent']))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.Link,            QColor(th['accent']))
    p.setColor(QPalette.LinkVisited,     QColor(th['accent_2']))
    # Disabled state — keep readable on dark backgrounds
    p.setColor(QPalette.Disabled, QPalette.Text,       QColor(th['fg_mute']))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(th['fg_mute']))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(th['fg_mute']))
    app.setPalette(p)


def app_qss(theme: str | None = None) -> str:
    """Generate the global QApplication-level stylesheet."""
    th = THEMES.get(theme or _current, THEMES["light"])
    return f"""
QWidget        {{ background:{th['bg']}; color:{th['fg']}; font-family:'Segoe UI'; font-size:12px; }}
QMainWindow    {{ background:{th['bg_alt']}; }}
QScrollArea    {{ background:transparent; border:none; }}

QLabel#section {{ color:{th['fg_dim']}; font-size:15px; font-weight:bold; letter-spacing:2px; }}
QLabel#hdrtext {{ color:{th['fg']}; font-weight:bold; font-size:12px; }}

QLineEdit      {{ background:{th['input_bg']}; border:1px solid {th['input_br']}; border-radius:2px;
                   padding:3px 6px; color:{th['fg']}; font-family:'Consolas'; font-size:12px; }}
QLineEdit:read-only {{ background:{th['input_bg']}; }}

QSpinBox, QDoubleSpinBox {{
    background:{th['input_bg']}; border:1px solid {th['input_br']}; color:{th['fg']};
    border-radius:2px; padding:3px 6px; font-family:'Consolas'; }}

QComboBox {{
    background:{th['input_bg']}; border:1px solid {th['input_br']}; color:{th['fg']};
    border-radius:2px; padding:4px 8px; min-width:120px; }}
QComboBox QAbstractItemView {{
    background:{th['card']}; color:{th['fg']}; selection-background-color:{th['accent_bg']};
    selection-color:{th['fg']}; border:1px solid {th['border']}; }}

QCheckBox {{ color:{th['fg']}; spacing:8px; padding:4px 0; }}
QCheckBox::indicator {{ width:16px; height:16px; border:1.5px solid {th['border']};
                          border-radius:3px; background:{th['input_bg']}; }}
QCheckBox::indicator:checked {{ background:{th['accent']}; border-color:{th['accent']}; }}

QPushButton {{ background:{th['input_bg']}; border:1px solid {th['border']}; border-radius:2px;
                padding:5px 10px; color:{th['fg']}; font-size:12px; }}
QPushButton:hover {{ background:{th['topbtn_hov']}; }}
QPushButton:disabled {{ color:{th['fg_mute']}; background:{th['card_alt']}; }}

QPushButton#topbtn {{ padding:6px 16px; background:{th['topbtn']}; border:1px solid {th['border']};
                       font-weight:bold; color:{th['fg']}; }}
QPushButton#topbtn:checked {{ background:{th['accent']}; color:#FFFFFF; border-color:{th['accent']}; }}
QPushButton#topbtn:hover {{ background:{th['topbtn_hov']}; }}
QPushButton#topbtn:checked:hover {{ background:{th['accent_2']}; }}

QFrame#group   {{ background:{th['card']}; border:1px solid {th['border']}; border-radius:2px; }}

QLabel.green   {{ background:{th['ok_bg']};   padding:3px 6px; border:1px solid {th['ok']}; color:{th['fg']}; }}
QLabel.yellow  {{ background:{th['warn_bg']}; padding:3px 6px; border:1px solid {th['warn']}; color:{th['fg']}; }}
QLabel.blue    {{ background:{th['info_bg']}; padding:3px 6px; border:1px solid {th['accent']}; color:#FFFFFF; }}
QLabel.red     {{ background:{th['err_bg']};  padding:3px 6px; border:1px solid {th['err']}; color:#FFFFFF; }}
QLabel.gray    {{ background:{th['card_alt']};padding:3px 6px; border:1px solid {th['border']}; color:{th['fg']}; }}

QTableWidget {{ background:{th['card']}; color:{th['fg']}; gridline-color:{th['border_lt']};
                 alternate-background-color:{th['card_alt']}; font-size:12px;
                 selection-background-color:{th['accent_bg']}; selection-color:{th['fg']}; }}
QTableWidget::item {{ padding:5px 8px; }}
QHeaderView::section {{ background:{th['card_alt']}; color:{th['fg']};
                          border:1px solid {th['border']}; padding:6px; font-weight:bold; }}

/* Cards in Advance / Settings — styled via object name so the rule lives in
   the app stylesheet (NOT inline on each card). Inline parent stylesheets
   intercept the styling responsibility for the entire subtree, which broke
   form widgets inside cards (they kept Fusion's light defaults). */
QFrame#ad_card {{ background:{th['card']}; border:1px solid {th['border_lt']};
                   border-radius:10px; }}
QFrame#ad_hero {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                   stop:0 {th['card']}, stop:1 {th['card_alt']});
                   border:1px solid {th['border_lt']}; border-radius:10px; }}
"""
