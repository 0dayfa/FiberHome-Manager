# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for FiberHome Manager — Beta
# Run via: pyinstaller FiberHomeManager.spec --noconfirm
# (build.bat wraps this with the requirements install + nice output.)

a = Analysis(
    ['designs\\d01_engineering\\main.py'],
    pathex=['.', 'shared', 'designs/d01_engineering'],
    binaries=[],
    datas=[('shared/assets/logo.svg',      'shared/assets'),
            ('shared/assets/logo_icon.svg', 'shared/assets')],
    hiddenimports=[
        # PyQt5 + WebEngine (Chromium runtime)
        'PyQt5.sip', 'sip',
        'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PyQt5.QtSvg', 'PyQt5.QtNetwork', 'PyQt5.QtPrintSupport',
        'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore', 'PyQt5.QtWebChannel',
        # First-party shared modules — listed explicitly because they're
        # imported lazily (inside functions) so PyInstaller's static
        # analyser can miss them otherwise.
        'shared.themes', 'shared.auth_store', 'shared.login_view',
        'shared.i18n', 'shared.network_tools', 'shared.ip_workers',
        'shared.fast_speed_test', 'shared.preflight',
        'shared.preflight_view', 'shared.debug_log',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FiberHome Manager - Beta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FiberHome Manager - Beta',
)
