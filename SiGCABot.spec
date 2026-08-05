# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# SiGCABot — Archivo de especificación de PyInstaller
# =============================================================================
# Empaqueta la aplicación como un ejecutable único portable de Windows.
#
# Los recursos estáticos (imágenes) se incluyen dentro del ejecutable.
# Los archivos del usuario (.env, config.json, status.json, logs/, evidence/)
# residen externamente junto al .exe para facilitar su persistencia.
#
# Uso:
#   pyinstaller SiGCABot.spec --noconfirm
#   o simplemente ejecutar: build.bat
# =============================================================================

a = Analysis(
    ['app_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('bender_chef.png', '.'),
        ('robot_hamburger_icon.png', '.'),
        ('images_info', 'images_info'),
    ],

    hiddenimports=[
        'src',
        'src.config',
        'src.logger',
        'src.state',
        'src.notifications',
        'src.bot_engine',
        'src.job_lock',
        'src.health_server',
        'src.telegram_poller',
        'src.scheduler',
        'plyer.platforms',
        'plyer.platforms.win.notification',
        'plyer.platforms.win.libs.balloontip',
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
    a.binaries,
    a.datas,
    [],
    name='SiGCABot',
    icon='robot_hamburger_icon.ico',
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
