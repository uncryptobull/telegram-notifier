import queue
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from . import __version__
from .service import Service
from .settings import Settings
from .windows import notify


class Application(tk.Tk):
    def __init__(self, store, demo=False, tray=True):
        super().__init__()
        self.store = store
        self.demo = demo
        self.messages = queue.Queue()
        self.service = None
        self.tray = None
        self.exiting = False
        self.contacts = {}
        self.bot_name = None
        self.account_name = "Not connected"
        self.monitoring = False
        self.setup_complete = False
        self.settings = Settings()
        load_failed = False
        if not demo:
            try:
                self.settings = store.read()
            except Exception:
                load_failed = True
        self.title("Telegram Notifier — Sample data" if demo else "Telegram Notifier")
        self.geometry("760x650")
        self.minsize(700, 600)
        self.configure(bg="#f2f3f5")
        self._style()
        icon = Path(__file__).with_name("assets") / "app.ico"
        if icon.exists():
            self.iconbitmap(str(icon))
        self.status = tk.StringVar(value="Ready")
        self.contact_status = tk.StringVar(value="Choose a contact to begin")
        self.account_status = tk.StringVar(value="Sign in to your Telegram account")
        self.fields = {}
        self.preferences = {}
        self.locked = []
        self._menu()
        self._layout()
        if self.settings.session:
            self.account_status.set("Saved session available")
        if load_failed:
            self.write("Saved sign-in could not be opened. Enter your details on the Account tab.")
            self.tabs.select(self.account_tab)
        elif not self.settings.session:
            self.tabs.select(self.account_tab)
            self.write("Connect your account, then select a contact on the Monitor tab.")
        else:
            self.write("Ready. Click Connect to refresh your chats, or Start monitoring to resume.")
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        if tray and not demo:
            self._start_tray()
        if demo:
            self._demo()
        self.after(100, self._drain)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        self.option_add("*Font", "{Segoe UI} 10")
        style.configure("TFrame", background="#f2f3f5")
        style.configure("TLabel", background="#f2f3f5", foreground="#263441")
        style.configure("Muted.TLabel", foreground="#677582")
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("TCheckbutton", background="#f2f3f5")
        style.configure("TLabelframe", background="#f2f3f5")
        style.configure("TLabelframe.Label", foreground="#263441", background="#f2f3f5")
        style.configure("TNotebook", background="#f2f3f5", tabmargins=(0, 6, 0, 0))
        style.configure("TNotebook.Tab", padding=(20, 8))
        style.configure("TButton", padding=(10, 5))
        style.configure("TEntry", padding=5)

    def _menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Start monitoring", command=self.start)
        file_menu.add_command(label="Stop monitoring", command=self.stop)
        file_menu.add_separator()
        file_menu.add_command(label="Minimize to tray", command=self.hide)
        file_menu.add_command(label="Exit", command=self.exit)
        menu.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(
            label="Get Telegram API details", command=lambda: webbrowser.open("https://my.telegram.org/apps")
        )
        help_menu.add_command(
            label="Create an alert bot", command=lambda: webbrowser.open("https://t.me/BotFather")
        )
        help_menu.add_separator()
        help_menu.add_command(label="Sample preview", command=self.preview)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "Telegram Notifier",
                f"Telegram Notifier {__version__}\nWindows online and typing notifications.\n\nIndependent software. Not affiliated with Telegram.",
            ),
        )
        menu.add_cascade(label="Help", menu=help_menu)
        self.configure(menu=menu)

    def _layout(self):
        frame = ttk.Frame(self, padding=(20, 16, 20, 10))
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Telegram Notifier", style="Title.TLabel").pack(anchor="w")
        self.tabs = ttk.Notebook(frame)
        self.tabs.pack(fill="both", expand=True, pady=(12, 0))
        self.monitor_tab = ttk.Frame(self.tabs, padding=18)
        self.account_tab = ttk.Frame(self.tabs, padding=18)
        self.settings_tab = ttk.Frame(self.tabs, padding=18)
        for tab, title in [
            (self.monitor_tab, "Monitor"),
            (self.account_tab, "Account"),
            (self.settings_tab, "Settings"),
        ]:
            self.tabs.add(tab, text=title)
        self._monitor()
        self._account()
        self._settings()
        status = ttk.Frame(self, padding=(20, 6))
        status.pack(fill="x", side="bottom")
        ttk.Label(status, textvariable=self.status).pack(side="left")
        ttk.Label(status, text=f"Version {__version__}", style="Muted.TLabel").pack(side="right")

    def _monitor(self):
        parent = self.monitor_tab
        ttk.Label(parent, textvariable=self.contact_status, font=("Segoe UI Semibold", 11)).pack(
            anchor="w", pady=(0, 14)
        )
        ttk.Label(parent, text="Contact").pack(anchor="w")
        self.target = tk.StringVar(value=self.settings.target_name or self.settings.target)
        self.contact_entry = ttk.Combobox(parent, textvariable=self.target)
        self.contact_entry.pack(fill="x", pady=(5, 5))
        self.locked.append(self.contact_entry)
        ttk.Label(
            parent,
            text="Enter @username, or connect your account to choose a recent chat.",
            style="Muted.TLabel",
        ).pack(anchor="w")
        events_frame = ttk.Frame(parent)
        events_frame.pack(fill="x", pady=16)
        for key, label in [("online", "Comes online"), ("typing", "Starts typing in your chat")]:
            self._check(events_frame, key, label).pack(side="left", padx=(0, 24))
        buttons = ttk.Frame(parent)
        buttons.pack(fill="x")
        self.start_button = ttk.Button(buttons, text="Start monitoring", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(buttons, text="Test Windows", command=lambda: self.test("windows")).pack(side="right")
        self.test_bot = ttk.Button(buttons, text="Test Telegram", command=lambda: self.test("telegram"))
        self.test_bot.pack(side="right", padx=8)
        ttk.Label(parent, text="Activity").pack(anchor="w", pady=(20, 6))
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(
            log_frame,
            height=8,
            wrap="word",
            state="disabled",
            bg="white",
            fg="#263441",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            font=("Segoe UI", 9),
        )
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)
        ttk.Button(parent, text="Clear activity", command=self.clear_activity).pack(anchor="e", pady=(6, 0))

    def _account(self):
        parent = self.account_tab
        ttk.Label(parent, textvariable=self.account_status, font=("Segoe UI Semibold", 11)).pack(
            anchor="w", pady=(0, 16)
        )
        grid = ttk.Frame(parent)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        for row, (key, label, secret) in enumerate(
            [
                ("api_id", "API ID", False),
                ("api_hash", "API hash", True),
                ("phone", "Phone (+country code)", True),
            ]
        ):
            self._field(grid, key, label, secret, row)
        ttk.Label(
            parent,
            text="Get your API ID and hash from my.telegram.org/apps.\nYour phone number is needed only for the first sign-in.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=12)
        account_buttons = ttk.Frame(parent)
        account_buttons.pack(fill="x")
        self.connect_button = ttk.Button(account_buttons, text="Connect account", command=self.connect)
        self.connect_button.pack(side="left")
        self.locked.append(self.connect_button)
        ttk.Button(
            account_buttons,
            text="API development tools",
            command=lambda: webbrowser.open("https://my.telegram.org/apps"),
        ).pack(side="left", padx=8)
        self.signout_button = ttk.Button(account_buttons, text="Sign out…", command=self.signout)
        self.signout_button.pack(side="right")
        self.locked.append(self.signout_button)
        ttk.Separator(parent).pack(fill="x", pady=22)
        self._check(parent, "remember", "Remember this account on this Windows user").pack(anchor="w")
        ttk.Label(
            parent,
            text="Saved credentials are encrypted by Windows. Login codes and\ntwo-step passwords are never written to disk.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=8)

    def _settings(self):
        parent = self.settings_tab
        ttk.Label(parent, text="Notification delivery", font=("Segoe UI Semibold", 11)).pack(
            anchor="w", pady=(0, 10)
        )
        self._check(parent, "desktop", "Windows notifications").pack(anchor="w", pady=4)
        self._check(parent, "telegram", "Send notifications through my Telegram bot").pack(anchor="w", pady=4)
        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(10, 0))
        grid.columnconfigure(1, weight=1)
        self._field(grid, "bot_token", "Bot token", True, 0)
        links = ttk.Frame(parent)
        links.pack(fill="x", pady=8)
        ttk.Button(links, text="Create bot", command=lambda: webbrowser.open("https://t.me/BotFather")).pack(
            side="left"
        )
        self.open_bot = ttk.Button(links, text="Open my bot", command=self.open_alert_bot, state="disabled")
        self.open_bot.pack(side="left", padx=8)
        ttk.Label(
            parent,
            text="Create a bot using /newbot in BotFather, then press Start in its chat.\nTelegram delivery is optional; Windows notifications work on their own.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 16))
        interval = ttk.Frame(parent)
        interval.pack(fill="x")
        ttk.Label(interval, text="Minimum interval per event").pack(side="left")
        self.cooldown = tk.IntVar(value=self.settings.cooldown)
        spin = ttk.Spinbox(interval, from_=5, to=300, width=6, textvariable=self.cooldown)
        spin.pack(side="left", padx=(12, 6))
        ttk.Label(interval, text="seconds").pack(side="left")
        self.locked.append(spin)
        ttk.Separator(parent).pack(fill="x", pady=18)
        self._check(parent, "close_to_tray", "Close the window to the system tray").pack(anchor="w", pady=4)
        self._check(parent, "private_preview", "Hide contact names in status and notifications").pack(
            anchor="w", pady=4
        )
        ttk.Label(
            parent,
            text="Online visibility follows Telegram privacy settings. Typing alerts\ncover only your private conversation. No message contents are logged.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=14)
        self.save_button = ttk.Button(parent, text="Save settings", command=self.save_preferences)
        self.save_button.pack(anchor="e")
        self.locked.append(self.save_button)

    def _field(self, parent, key, label, secret, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=6)
        var = tk.StringVar(value=str(getattr(self.settings, key, "")))
        entry = ttk.Entry(parent, textvariable=var, show="•" if secret else "")
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        self.fields[key] = var
        self.locked.append(entry)

    def _check(self, parent, key, label):
        var = tk.BooleanVar(value=getattr(self.settings, key))
        self.preferences[key] = var
        control = ttk.Checkbutton(parent, text=label, variable=var)
        self.locked.append(control)
        return control

    def collect(self):
        cfg = replace(self.settings)
        for key, var in self.fields.items():
            if key != "phone":
                setattr(cfg, key, var.get().strip())
        for key, var in self.preferences.items():
            setattr(cfg, key, var.get())
        cfg.cooldown = self.cooldown.get()
        value = self.target.get().strip()
        if value in self.contacts:
            cfg.target = str(self.contacts[value])
        elif value != self.settings.target_name:
            cfg.target = value
            cfg.target_name = ""
        return cfg

    def save_preferences(self):
        try:
            cfg = self.collect()
            if not 5 <= cfg.cooldown <= 300:
                raise ValueError("Choose an interval between 5 and 300 seconds.")
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Check settings", str(exc), parent=self)
            return
        self.settings = cfg
        self._persist()
        self.write("Settings saved for the next monitoring session.")

    def _persist(self):
        if self.demo:
            return
        try:
            self.store.write(self.settings)
        except OSError:
            self.write(
                "Windows could not save the profile securely. The sign-in remains available in memory until you exit."
            )

    def _begin(self, mode):
        if self.demo or self.service and self.service.is_alive():
            return
        try:
            cfg = self.collect()
            cfg.validate(self.fields["phone"].get().strip(), connecting=mode == "connect")
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Check your settings", str(exc), parent=self)
            if not self.settings.session:
                self.tabs.select(self.account_tab)
            return
        self.settings = cfg
        self.setup_complete = False
        self._busy(True)
        self.service = Service(cfg, self.fields["phone"].get().strip(), self.emit, mode)
        self.service.start()

    def connect(self):
        self._begin("connect")

    def start(self):
        self._begin("watch")

    def stop(self):
        if self.service and self.service.is_alive():
            self.status.set("Stopping…")
            self.service.stop()

    def test(self, route):
        if self.demo:
            self.write("Sample mode: no notifications were sent.")
            return
        if route == "telegram":
            if not self.preferences["telegram"].get():
                self.write("Enable Telegram delivery on the Settings tab first.")
            elif self.monitoring and self.service:
                self.service.commands.put(route)
            else:
                self.write("Start monitoring before testing Telegram delivery.")
            return

        def submit():
            try:
                notify("Test notification", "Telegram Notifier desktop notifications are working.")
                self.emit(
                    "log",
                    "Windows test submitted. Check Notification Center if Do Not Disturb hides the banner.",
                )
            except Exception as exc:
                self.emit(
                    "log", str(exc) if isinstance(exc, RuntimeError) else "Windows notification test failed."
                )

        threading.Thread(target=submit, daemon=True, name="notification-test").start()

    def signout(self):
        if self.demo or self.service and self.service.is_alive():
            return
        if not self.settings.session:
            self.forget()
            return
        if messagebox.askyesno(
            "Sign out", "Revoke this app's Telegram session and remove its saved profile?", parent=self
        ):
            self._busy(True)
            self.service = Service(self.settings, "", self.emit, "logout")
            self.service.start()

    def forget(self):
        try:
            self.store.clear()
        except OSError:
            self.write("Could not remove the saved profile. Check access to the app's data folder.")
            return
        self.settings = Settings()
        self.contacts.clear()
        self.target.set("")
        self.account_status.set("Not connected")
        self.contact_status.set("Choose a contact to begin")
        self.account_name = "Not connected"
        for var in self.fields.values():
            var.set("")
        self.contact_entry.configure(values=())
        self.bot_name = None
        self.open_bot.configure(state="disabled")
        self.clear_activity()
        self.write("Signed out. The saved profile was removed.")

    def open_alert_bot(self):
        if self.bot_name:
            webbrowser.open("https://t.me/" + self.bot_name)

    def preview(self):
        if getattr(sys, "frozen", False):
            args = [sys.executable, "--demo"]
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            args = [str(pythonw), str(Path(__file__).resolve().parents[1] / "run.pyw"), "--demo"]
        subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)

    def _busy(self, active):
        for control in self.locked + [self.start_button]:
            control.configure(state="disabled" if active else "normal")
        self.stop_button.configure(state="normal" if active else "disabled")

    def emit(self, kind, value=None):
        self.messages.put((kind, value))

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", datetime.now().strftime("%H:%M:%S") + "  " + text + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 200:
            self.log.delete("1.0", "2.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_activity(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _start_tray(self):
        try:
            import pystray
            from PIL import Image

            def command(kind):
                return lambda icon, item: self.emit(kind)

            self.tray = pystray.Icon(
                "TelegramNotifier",
                Image.open(Path(__file__).with_name("assets") / "app.png"),
                "Telegram Notifier",
                pystray.Menu(
                    pystray.MenuItem("Open Telegram Notifier", command("show"), default=True),
                    pystray.MenuItem("Start monitoring", command("start")),
                    pystray.MenuItem("Stop monitoring", command("stop")),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Exit", command("exit")),
                ),
            )
            self.tray.run_detached()
        except Exception:
            self.tray = None
            self.write("System tray unavailable. Closing the window will exit the app.")

    def hide(self):
        if self.tray and self.tray.visible:
            self.withdraw()
        else:
            self.iconify()

    def show(self):
        self.deiconify()
        self.lift()

    def close_window(self):
        if self.preferences["close_to_tray"].get() and self.tray and self.tray.visible:
            self.hide()
        else:
            self.exit()

    def exit(self):
        if self.exiting:
            return
        self.exiting = True
        self.stop()
        if self.tray:
            self.tray.stop()
        self.status.set("Exiting…")

    def _drain(self):
        for _ in range(100):
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.write(value)
            elif kind == "status":
                self.status.set(value)
            elif kind == "settings":
                self.settings = value
                self._persist()
            elif kind == "account":
                self.account_name = value
                self.account_status.set(
                    "Account connected" if self.settings.private_preview else "Connected as " + value
                )
                self.fields["phone"].set("")
            elif kind == "contacts":
                self.contacts = {f"{name}  [{uid}]": uid for uid, name in value}
                self.contact_entry.configure(values=list(self.contacts))
            elif kind == "watching":
                self.monitoring = True
                self.contact_status.set("Monitoring: " + value)
            elif kind == "bot":
                self.bot_name = value
                self.open_bot.configure(state="normal")
                self.write("Telegram bot ready. Press Start in its chat before testing delivery.")
            elif kind == "prompt":
                title, text, secret, future = value
                self.show()
                if not future.done():
                    answer = simpledialog.askstring(title, text, show="•" if secret else None, parent=self)
                    if not future.done():
                        future.set_result(answer)
            elif kind == "signed_out":
                self.forget()
            elif kind == "setup_complete":
                self.setup_complete = True
                self.tabs.select(self.monitor_tab)
                self.contact_status.set("Account connected. Select a contact, then Start monitoring.")
            elif kind == "finished":
                self.monitoring = False
                self._busy(False)
                self.status.set("Ready" if self.settings.session else "Not connected")
                if self.setup_complete:
                    self.status.set("Ready to monitor")
                else:
                    self.contact_status.set("Monitoring stopped")
                    self.write(
                        "Monitoring stopped."
                        if self.service and self.service.mode == "watch"
                        else "Setup connection ended."
                    )
            elif kind in ("show", "start", "stop", "exit"):
                getattr(self, kind)()
        if self.exiting and not (self.service and self.service.is_alive()):
            self.destroy()
        else:
            self.after(100, self._drain)

    def _demo(self):
        self.tabs.select(self.monitor_tab)
        self.contact_entry.configure(values=("Alex Morgan", "Sam Parker"))
        self.target.set("Alex Morgan")
        self.contact_status.set("Monitoring: Alex Morgan")
        self.status.set("Monitoring · Sample data")
        self.clear_activity()
        for text in [
            "Account connected.",
            "Monitoring started.",
            "Alex Morgan came online.",
            "Windows notification submitted.",
            "Alex Morgan started typing in your chat.",
            "Telegram notification sent.",
        ]:
            self.write(text)
