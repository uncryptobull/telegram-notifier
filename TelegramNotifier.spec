from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'run.pyw')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'telegram_notifier' / 'notify.ps1'), 'telegram_notifier'),
           (str(root / 'telegram_notifier' / 'assets'), 'telegram_notifier/assets')],
    hiddenimports=['pystray._win32', 'PIL._tkinter_finder'],
    excludes=['pytest', 'ruff', 'pip_audit', 'setuptools', 'PIL.ImageQt', 'PySide6', 'PyQt6', 'numpy'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='TelegramNotifier', console=False, debug=False,
    strip=False, upx=False,
    icon=str(root / 'telegram_notifier' / 'assets' / 'app.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='TelegramNotifier')
