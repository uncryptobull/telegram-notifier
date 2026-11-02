import asyncio
import concurrent.futures
import queue
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone

from telethon import TelegramClient, errors, events, types
from telethon.sessions import StringSession

from .bot import AlertBot, BotDeliveryError
from .events import Gate
from .windows import notify


def error_message(exc):
    messages = {
        "PhoneCodeInvalidError": "Incorrect login code. Connect again to retry.",
        "PhoneCodeExpiredError": "The login code expired. Connect again for a new code.",
        "PasswordHashInvalidError": "Incorrect two-step verification password.",
        "ApiIdInvalidError": "Check the API ID and API hash.",
        "PhoneNumberInvalidError": "Check your phone number and country code.",
        "FloodWaitError": "Telegram requested a delay. Wait before trying again.",
        "AuthKeyUnregisteredError": "This session was revoked. Connect your account again.",
        "SessionRevokedError": "This session was revoked. Connect your account again.",
        "UserDeactivatedBanError": "Telegram restricted this account. Check the official app.",
        "ValueError": "User not found. Select a recent chat or enter an exact @username.",
        "TimeoutError": "The connection timed out. Check your internet connection and try again.",
    }
    return messages.get(
        type(exc).__name__, "Telegram could not complete the request (" + type(exc).__name__ + ")."
    )


class Service(threading.Thread):
    def __init__(self, settings, phone, emit, mode="watch"):
        super().__init__(daemon=True, name="telegram-connection")
        self.settings = replace(settings)
        self.phone = phone
        self.emit = emit
        self.mode = mode
        self.commands = queue.Queue()
        self.stopping = threading.Event()
        self.loop = None
        self.task = None
        self.pending = None

    def stop(self):
        self.stopping.set()
        if self.pending:
            self.pending.cancel()
        if self.loop and self.task:
            try:
                self.loop.call_soon_threadsafe(self.task.cancel)
            except RuntimeError:
                pass

    async def prompt(self, title, text, secret=False):
        future = concurrent.futures.Future()
        self.pending = future
        self.emit("prompt", (title, text, secret, future))
        try:
            answer = await asyncio.wait_for(asyncio.wrap_future(future), 180)
            if answer is None:
                raise asyncio.CancelledError()
            return answer.strip()
        finally:
            self.pending = None

    def run(self):
        try:
            asyncio.run(self.supervise())
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.emit("log", error_message(exc))
        finally:
            self.phone = ""
            self.emit("finished", None)

    async def supervise(self):
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        delay = 2
        while not self.stopping.is_set():
            try:
                await self.connect()
                return
            except (OSError, ConnectionError, asyncio.TimeoutError):
                if self.mode != "watch" or not self.settings.session:
                    raise
                self.emit("status", "Reconnecting…")
                self.emit(
                    "log",
                    f"Connection lost. Retrying in {delay} seconds; events during the gap may be missed.",
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def connect(self):
        cfg = self.settings
        client = TelegramClient(
            StringSession(cfg.session),
            int(cfg.api_id),
            cfg.api_hash,
            request_retries=2,
            connection_retries=3,
            timeout=15,
            flood_sleep_threshold=0,
            device_model="Telegram Notifier",
            app_version="0.2.0",
        )
        try:
            self.emit("status", "Connecting…")
            await asyncio.wait_for(client.connect(), 35)
            if self.mode == "logout":
                if await client.is_user_authorized():
                    await client.log_out()
                self.emit("signed_out", None)
                return
            if not await client.is_user_authorized():
                await client.send_code_request(self.phone)
                code = await self.prompt("Telegram login", "Enter the code Telegram sent to your account.")
                try:
                    await client.sign_in(self.phone, code)
                except errors.SessionPasswordNeededError:
                    password = await self.prompt(
                        "Two-step verification", "Enter your Telegram two-step verification password.", True
                    )
                    await client.sign_in(password=password)
                    password = None
            me = await client.get_me()
            cfg.session = client.session.save()
            self.emit("settings", replace(cfg))
            self.emit("account", " ".join(filter(None, [me.first_name, me.last_name])) or "Connected")
            self.phone = ""
            dialogs = await client.get_dialogs(limit=200)
            self.emit(
                "contacts",
                [(d.id, d.name) for d in dialogs if d.is_user and d.id != me.id and not d.entity.bot],
            )
            if self.mode == "connect":
                self.emit("log", "Account connected. Choose a contact on the Monitor tab.")
                return
            value = cfg.target.strip()
            target = await client.get_entity(int(value) if value.isdecimal() else value.lstrip("@"))
            if not isinstance(target, types.User) or target.bot or target.id == me.id:
                self.emit("log", "Choose another person rather than your own account or a bot.")
                return
            name = " ".join(filter(None, [target.first_name, target.last_name])) or str(target.id)
            cfg.target_name = name
            cfg.target = str(target.id)
            self.emit("settings", replace(cfg))
            bot = AlertBot(cfg.bot_token) if cfg.telegram else None
            if bot:
                try:
                    self.emit("bot", await asyncio.to_thread(bot.identity))
                except BotDeliveryError as exc:
                    self.emit("log", str(exc))
            gate = Gate(cooldown=cfg.cooldown)

            def expiry(status):
                return time.monotonic() + max(
                    0, (status.expires - datetime.now(timezone.utc)).total_seconds()
                )

            if isinstance(target.status, types.UserStatusOnline):
                gate.status(True, expiry(target.status), enabled=False)
            else:
                gate.status(False, enabled=False)
            outbound = asyncio.Queue(maxsize=30)

            async def deliver(title, text, route="both"):
                if cfg.desktop and route in ("both", "windows"):
                    try:
                        await asyncio.to_thread(notify, title, text)
                        self.emit("log", "Windows notification submitted.")
                    except Exception as exc:
                        self.emit(
                            "log",
                            str(exc)
                            if isinstance(exc, RuntimeError)
                            else "Windows delivery failed. Try again or check notification settings.",
                        )
                if cfg.telegram and route in ("both", "telegram"):
                    try:
                        await asyncio.to_thread(bot.send, me.id, title, text)
                        self.emit("log", "Telegram notification sent.")
                    except BotDeliveryError as exc:
                        self.emit("log", str(exc))

            async def sender():
                while True:
                    await deliver(*(await outbound.get()))

            async def on_update(event):
                if event.user_id != target.id:
                    return
                label = "Your selected contact" if cfg.private_preview else name
                alert = None
                if event.status is not None:
                    online = isinstance(event.status, types.UserStatusOnline)
                    if gate.status(online, expiry(event.status) if online else 0, cfg.online):
                        alert = ("Online", label + " came online.")
                if event.action is not None and event.chat_id == target.id:
                    if gate.typing(bool(event.typing), cfg.typing):
                        alert = ("Typing", label + " started typing in your chat.")
                if alert:
                    self.emit("log", alert[1])
                    try:
                        outbound.put_nowait((*alert, "both"))
                    except asyncio.QueueFull:
                        self.emit("log", "The delivery queue is full. One notification was skipped.")

            client.add_event_handler(on_update, events.UserUpdate())
            sender_task = asyncio.create_task(sender())
            self.emit("status", "Monitoring")
            self.emit("watching", "Selected contact" if cfg.private_preview else name)
            self.emit("log", "Monitoring started. An already-online contact is used as the initial baseline.")
            try:
                while not self.stopping.is_set():
                    if client.disconnected.done():
                        raise ConnectionError()
                    try:
                        route = self.commands.get_nowait()
                        outbound.put_nowait(("Test notification", "Telegram Notifier is connected.", route))
                    except queue.Empty:
                        pass
                    except asyncio.QueueFull:
                        self.emit("log", "The notification queue is busy. Please wait before testing again.")
                    await asyncio.sleep(0.25)
            finally:
                sender_task.cancel()
                await asyncio.gather(sender_task, return_exceptions=True)
                client.remove_event_handler(on_update)
        finally:
            await client.disconnect()
