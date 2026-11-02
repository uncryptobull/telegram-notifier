import base64
import json
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen


def diagnose():
    result = {"frozen": bool(getattr(sys, "frozen", False))}
    try:
        with urlopen("https://api.telegram.org", timeout=15) as response:
            result["https"] = response.status
    except Exception as exc:
        reason = getattr(exc, "reason", None)
        result["https"] = {
            "type": type(exc).__name__,
            "reason": type(reason).__name__,
            "errno": getattr(reason, "errno", None),
            "verify": getattr(reason, "verify_message", None),
        }
    try:
        result["certificates"] = len(ssl.create_default_context().get_ca_certs())
    except Exception as exc:
        result["certificates"] = {"error": type(exc).__name__}
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as temporary:
        payload = base64.b64encode(
            json.dumps(
                {"python": sys.executable, "arguments": "", "app": str(root / "ui.py"), "xml": "<toast/>"}
            ).encode()
        ).decode()
        response = subprocess.run(
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
                "-RegisterOnly",
                "-ShortcutPath",
                str(Path(temporary) / "probe.lnk"),
            ],
            capture_output=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        error = response.stderr.decode(errors="replace").replace(str(Path.home()), "[user]")
        result["windows"] = {"code": response.returncode, "error": error[:1600]}
    return result
