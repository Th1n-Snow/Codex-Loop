# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys
import os
import PySide6

# Keep unrelated PDF/image tools on the developer's PATH out of the release.
if sys.platform == "win32":
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    os.environ["PATH"] = os.pathsep.join((sys.base_prefix, str(Path(PySide6.__file__).parent),
                                         str(windows / "System32"), str(windows)))

root = Path(SPEC).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from sentinel.product import PRODUCT

a = Analysis(
    [str(root / "packaging" / "entrypoint.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[
        (str(root / "src" / "sentinel" / "assets" / "codex-loop-dawn.png"), "sentinel/assets"),
        (str(root / "LICENSE"), "."),
        (str(root / "THIRD_PARTY_NOTICES.md"), "."),
        (str(root / "licenses"), "licenses"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# Qt's official Windows wheel links Qt6Core to the Windows system ICU DLL. A
# different generic icuuc.dll on PATH (for example, Poppler's) can be discovered
# by PyInstaller and copied beside the app, where it shadows System32 and fails
# at load time with WinError 127. Never redistribute that unrelated runtime.
_system_icu_names = {"icudt.dll", "icudt78.dll", "icuuc.dll"}
a.binaries = [
    entry for entry in a.binaries if Path(entry[0]).name.lower() not in _system_icu_names
    and Path(entry[0]).name.lower() not in {"ucrtbase.dll", "qopensslbackend.dll", "libssl-3-x64.dll", "libcrypto-3-x64.dll"}
    and not Path(entry[0]).name.lower().startswith("api-ms-win-")
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=Path(PRODUCT.executable_name).stem,
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
    icon=[str(root / "packaging" / PRODUCT.icon_filename)],
    version=str(root / "packaging" / PRODUCT.version_resource_filename),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=Path(PRODUCT.executable_name).stem,
)
