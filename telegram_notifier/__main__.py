import argparse
import ctypes
import json
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from .settings import ProfileStore
from .windows import SingleInstance


def main():
    parser = argparse.ArgumentParser(prog="TelegramNotifier")
    parser.add_argument(
        "--demo", action="store_true", help="Show sample data without connecting or saving anything"
    )
    parser.add_argument("--self-test", type=Path, metavar="REPORT", help=argparse.SUPPRESS)
    parser.add_argument("--diagnose", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.diagnose:
        from .diagnostics import diagnose

        args.diagnose.write_text(json.dumps(diagnose()), encoding="utf-8")
        return
    if os.name != "nt":
        parser.error("Telegram Notifier requires Windows 10 or later.")
    for key, folder in [("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")]:
        library = Path(sys.base_prefix) / "tcl" / folder
        if library.exists():
            os.environ[key] = "//?/" + library.as_posix()
        elif os.environ.get(key) and not os.environ[key].startswith("//?/"):
            os.environ[key] = "//?/" + Path(os.environ[key]).as_posix()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    instance = None
    try:
        if not args.demo and not args.self_test:
            instance = SingleInstance()
            if instance.already_running:
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo(
                    "Telegram Notifier",
                    "Telegram Notifier is already running. Open it from its icon in the system tray.",
                )
                root.destroy()
                return
        from .ui import Application

        if args.self_test:
            import tempfile

            with tempfile.TemporaryDirectory(prefix="notifier-test-") as temporary:
                app = Application(ProfileStore(temporary), tray=True)

                def finish_test():
                    app.tabs.select(app.monitor_tab)
                    app.update_idletasks()
                    report = {
                        "window": app.winfo_exists() == 1,
                        "tabs": len(app.tabs.tabs()),
                        "tray": bool(app.tray and app.tray.visible),
                        "frozen": bool(getattr(sys, "frozen", False)),
                        "console": bool(ctypes.windll.kernel32.GetConsoleWindow()),
                        "buttons_visible": app.start_button.winfo_ismapped() == 1,
                    }
                    args.self_test.write_text(json.dumps(report), encoding="utf-8")
                    app.exit()

                app.after(1800, finish_test)
                app.mainloop()
        else:
            app = Application(ProfileStore(), demo=args.demo)
            app.mainloop()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Telegram Notifier",
            "The application could not start ("
            + type(exc).__name__
            + ").\nExtract the complete release folder and try again.",
        )
        root.destroy()
    finally:
        if instance:
            instance.close()


if __name__ == "__main__":
    main()
