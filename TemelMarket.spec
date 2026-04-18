# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


def _dedupe_entries(entries):
    unique = []
    seen = set()
    for entry in entries:
        key = repr(entry)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return unique


project_root = Path(SPECPATH)
datas = [
    (str(project_root / "assets" / "temelmarket_icon.png"), "assets"),
    (str(project_root / "assets" / "temelmarket.ico"), "assets"),
    (str(project_root / "installer" / "install_webview2.ps1"), "."),
]
binaries = []
hiddenimports = []

for package_name in ("flet", "flet_desktop", "flet_web"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(
        name
        for name in package_hiddenimports
        if name != "flet.testing" and not name.startswith("flet.testing.")
    )

datas = _dedupe_entries(datas)
binaries = _dedupe_entries(binaries)
hiddenimports = _dedupe_entries(hiddenimports)

excludes = [
    "cookiecutter",
    "setuptools",
    "distutils",
    "tkinter",
    "_tkinter",
    "flet.testing",
]


a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TemelMarket",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_root / "assets" / "temelmarket.ico")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TemelMarket",
)
