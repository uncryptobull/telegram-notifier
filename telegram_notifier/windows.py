import base64
import ctypes
import json
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path
from xml.sax.saxutils import escape


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data, decrypt=False):
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dest = Blob()
    api = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        ok = api.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(dest))
    else:
        ok = api.CryptProtectData(
            ctypes.byref(source), "Telegram Notifier", None, None, None, 1, ctypes.byref(dest)
        )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(dest.data, dest.size)
    finally:
        kernel.LocalFree(dest.data)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(protect(json.dumps(value).encode()))
    temp.replace(path)


def load(path):
    return json.loads(protect(Path(path).read_bytes(), decrypt=True))


def notify(title, message):
    xml = (
        '<toast><visual><binding template="ToastGeneric"><text>'
        + escape(title)
        + "</text><text>"
        + escape(message)
        + "</text></binding></visual></toast>"
    )
    root = Path(__file__).resolve().parent
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    frozen = getattr(sys, "frozen", False)
    payload = base64.b64encode(
        json.dumps(
            {
                "xml": xml,
                "app": str(root / "app.py"),
                "python": sys.executable
                if frozen
                else str(pythonw if pythonw.exists() else Path(sys.executable)),
                "arguments": "" if frozen else '"' + str(root.parent / "run.pyw") + '"',
            }
        ).encode()
    ).decode()
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "notify.ps1"),
            "-PayloadBase64",
            payload,
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True,
        timeout=30,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        if "Windows notifications are blocked" in detail:
            raise RuntimeError(detail)
        raise RuntimeError(
            "Windows notification registration or delivery failed. Check Settings > System > Notifications."
        )


class SingleInstance:
    def __init__(self):
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        api.CreateMutexW.restype = wintypes.HANDLE
        self.handle = api.CreateMutexW(None, False, "Local\\TelegramNotifier.Desktop")
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.already_running = ctypes.get_last_error() == 183

    def close(self):
        if self.handle:
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            api.CloseHandle(self.handle)
            self.handle = None
