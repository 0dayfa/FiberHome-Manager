"""Login dialog used at app startup and after Logout."""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QCheckBox, QFrame)
from PyQt5.QtCore    import Qt

# Lazy import — i18n is shared, but importing it at module load time would
# pull in PyQt before SafeApp finishes setting up attributes on some hot paths.
def _t(key):
    try:
        from shared import i18n
        return i18n.s(key)
    except Exception:
        return key


class LoginDialog(QDialog):
    """Modal: collects username + password + remember toggle.
    Returns via .accepted_data = (user, pwd, remember) when accepted."""

    def __init__(self, ip="192.168.8.1",
                  default_user="superadmin",
                  default_pwd="",
                  default_remember=True,
                  parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{_t('AppName')} — {_t('Login')}")
        self.setModal(True)
        self.setFixedWidth(420)
        self.accepted_data = None
        self._build(ip, default_user, default_pwd, default_remember)

    def _build(self, ip, du, dp, dr):
        v = QVBoxLayout(self); v.setContentsMargins(28, 24, 28, 22); v.setSpacing(14)

        # Header
        title = QLabel(f"⚡  {_t('AppName')}")
        title.setStyleSheet("color:#0D47A1; font-size:22px; font-weight:bold;")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel(f"{_t('Sign in to')}  {ip}")
        sub.setStyleSheet("color:#78909C; font-size:11px;")
        sub.setAlignment(Qt.AlignCenter)
        v.addWidget(title); v.addWidget(sub)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet("background:#E0E4E8;")
        v.addWidget(sep)

        # Username
        v.addWidget(self._lbl(_t("Username")))
        self.f_user = QLineEdit(du)
        self.f_user.setMinimumHeight(34)
        v.addWidget(self.f_user)

        # Password
        v.addWidget(self._lbl(_t("Password")))
        self.f_pwd = QLineEdit(dp)
        self.f_pwd.setEchoMode(QLineEdit.Password)
        self.f_pwd.setMinimumHeight(34)
        self.f_pwd.returnPressed.connect(self._on_login)
        v.addWidget(self.f_pwd)

        # Save toggle
        self.f_save = QCheckBox(_t("Remember me"))
        self.f_save.setChecked(dr)
        v.addWidget(self.f_save)

        # Status line
        self.lbl_status = QLabel(" ")
        self.lbl_status.setStyleSheet("color:#C62828; font-size:11px;")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        v.addWidget(self.lbl_status)

        # Login button
        btn = QPushButton(_t("Login"))
        btn.setMinimumHeight(38)
        btn.setStyleSheet(
            "QPushButton { background:#0D47A1; color:#FFFFFF; border:none; "
            "border-radius:4px; font-size:13px; font-weight:bold; padding:8px; }"
            "QPushButton:hover { background:#1565C0; }"
            "QPushButton:pressed { background:#0B3A82; }")
        btn.clicked.connect(self._on_login)
        v.addWidget(btn)

        if du and dp:
            self.f_pwd.setFocus()
        else:
            self.f_user.setFocus()

    def _lbl(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#37474F; font-size:11px; font-weight:bold; letter-spacing:1px;")
        return l

    def _on_login(self):
        u = self.f_user.text().strip()
        p = self.f_pwd.text()
        if not u or not p:
            self.lbl_status.setText("Username and password are required.")
            return
        self.accepted_data = (u, p, self.f_save.isChecked())
        self.accept()

    def set_error(self, msg: str):
        self.lbl_status.setText(msg or "")
