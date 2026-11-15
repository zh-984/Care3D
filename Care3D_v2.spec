# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32', 'win32gui', 'win32con', 'win32api', 'win32process'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# These OS libraries must resolve to Windows 10/11, not similarly named codec
# libraries from an unrelated developer tool on PATH (notably ICU with renamed exports).
def is_system_library(entry):
    name = entry[0].replace('\\', '/').split('/')[-1].lower()
    return name in ('ucrtbase.dll', 'icuuc.dll', 'icuin.dll', 'icudt.dll') or name.startswith(('api-ms-win-', 'ext-ms-win-'))

a.binaries = [entry for entry in a.binaries if not is_system_library(entry)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Care3D_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
