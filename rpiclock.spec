# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['rpiclock.py'],
    pathex=[],
    binaries=[],
    datas=[('config.ini', '.'), ('blank.png', '.'), ('DSEG7Classic-Bold.ttf', '.'), ('owm_icons', 'owm_icons'), ('bom_icons', 'bom_icons')],
    hiddenimports=[],
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
    name='rpiclock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='rpiclock',
)
