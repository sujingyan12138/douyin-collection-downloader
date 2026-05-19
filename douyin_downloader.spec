# -*- mode: python ; coding: utf-8 -*-

hiddenimports = [
    "browser_cookie3",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome.webdriver",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.chrome.service",
    "selenium.webdriver.chromium.webdriver",
    "selenium.webdriver.chromium.options",
    "selenium.webdriver.chromium.remote_connection",
    "selenium.webdriver.chromium.service",
    "selenium.webdriver.edge.webdriver",
    "selenium.webdriver.edge.options",
    "selenium.webdriver.edge.service",
    "websocket",
]

datas = [
    ("config.json.example", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["setuptools"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="douyin-collection-downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
