import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from telethon import events, types

from telegram_notifier.service import Service
from telegram_notifier.settings import Settings


def test_real_telegram_events_filter_sender_group_and_repeats():
    output = []
    clients = []
    target = types.User(
        id=42, first_name="Sample", status=types.UserStatusOffline(datetime.now(timezone.utc))
    )

    class Client:
        def __init__(self, *args, **kwargs):
            self.session = SimpleNamespace(save=lambda: "sample-session")
            self.disconnected = asyncio.get_running_loop().create_future()
            clients.append(self)

        async def connect(self):
            pass

        async def disconnect(self):
            self.closed = True

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.User(id=1, first_name="Owner")

        async def get_dialogs(self, **kwargs):
            return []

        async def get_entity(self, value):
            return target

        def add_event_handler(self, callback, builder):
            async def feed():
                for uid, group in [(99, False), (42, True), (42, False), (42, False)]:
                    await callback(
                        events.UserUpdate.Event(
                            types.PeerUser(uid),
                            chat_peer=types.PeerChat(123) if group else None,
                            typing=types.SendMessageTypingAction(),
                        )
                    )
                event = events.UserUpdate.Event(
                    types.PeerUser(42),
                    status=types.UserStatusOnline(datetime.now(timezone.utc) + timedelta(seconds=60)),
                )
                await callback(event)
                await callback(event)
                await asyncio.sleep(0.05)
                service.stopping.set()

            asyncio.create_task(feed())

        def remove_event_handler(self, callback):
            pass

    cfg = Settings(
        api_id="100",
        api_hash="a" * 32,
        target="sample",
        desktop=True,
        telegram=True,
        bot_token="sample",
        private_preview=True,
    )
    service = Service(cfg, "", lambda kind, value: output.append((kind, value)))
    with (
        patch("telegram_notifier.service.TelegramClient", Client),
        patch("telegram_notifier.service.notify") as windows,
        patch("telegram_notifier.service.AlertBot") as bot,
    ):
        bot.return_value.identity.return_value = "sample_bot"
        service.run()
    logs = [value for kind, value in output if kind == "log"]
    assert logs.count("Your selected contact started typing in your chat.") == 1
    assert logs.count("Your selected contact came online.") == 1
    assert windows.call_count == 2
    assert bot.return_value.send.call_count == 2
    assert all(call.args[0] == 1 for call in bot.return_value.send.call_args_list)
    assert clients[0].closed
    assert not cfg.session
    assert any(kind == "settings" and value.session for kind, value in output)


def test_pending_login_can_be_cancelled():
    async def run():
        service = Service(Settings(), "", lambda *args: None)
        task = asyncio.create_task(service.prompt("Code", "Code"))
        await asyncio.sleep(0)
        service.stop()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("Login prompt did not cancel")

    asyncio.run(run())


def test_connect_mode_retains_session_in_memory_without_starting_watch():
    output = []

    class Client:
        def __init__(self, *args, **kwargs):
            self.session = SimpleNamespace(save=lambda: "sample-session")

        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return types.User(id=1, first_name="Owner")

        async def get_dialogs(self, **kwargs):
            return []

    service = Service(
        Settings(api_id="100", api_hash="a" * 32),
        "",
        lambda kind, value: output.append((kind, value)),
        "connect",
    )
    with patch("telegram_notifier.service.TelegramClient", Client):
        service.run()
    assert any(kind == "settings" and value.session == "sample-session" for kind, value in output)
    assert not any(kind == "watching" for kind, value in output)
    assert any(kind == "setup_complete" for kind, value in output)


def test_reconnection_uses_backoff_and_stops_after_success():
    attempts = []
    cfg = replace(Settings(), session="sample")
    service = Service(cfg, "", lambda *args: None)

    async def connect():
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError()

    async def no_wait(delay):
        assert delay == 2

    with patch.object(service, "connect", connect), patch("telegram_notifier.service.asyncio.sleep", no_wait):
        asyncio.run(service.supervise())
    assert len(attempts) == 2
