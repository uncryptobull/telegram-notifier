import base64
import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from xml.etree import ElementTree

import pytest

from telegram_notifier.bot import AlertBot, BotDeliveryError
from telegram_notifier.windows import notify


def test_bot_uses_explicit_recipient_and_plain_text():
    with patch.object(AlertBot, "call", return_value={}) as call:
        AlertBot("sample").send(77, "Typing", "A <name> is typing")
    assert call.call_args.args == ("sendMessage", {"chat_id": 77, "text": "Typing\nA <name> is typing"})


@pytest.mark.parametrize("status,expected", [(403, "press Start"), (429, "limited"), (401, "token")])
def test_bot_errors_are_actionable_and_never_expose_token(status, expected):
    with patch(
        "telegram_notifier.bot.urlopen",
        side_effect=HTTPError("https://example.com/secret", status, "error", {}, None),
    ):
        with pytest.raises(BotDeliveryError, match=expected) as error:
            AlertBot("secret").send(77, "Online", "Message")
    assert "secret" not in str(error.value)


def test_windows_payload_escapes_untrusted_names_and_uses_argument_list():
    with patch("telegram_notifier.windows.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run:
        notify("Typing <&>", "Name '& <> $() is typing")
    args = run.call_args.args[0]
    assert isinstance(args, list)
    payload = json.loads(base64.b64decode(args[-1]))
    xml = ElementTree.fromstring(payload["xml"])
    assert xml.findall(".//text")[1].text == "Name '& <> $() is typing"
    assert "EncodedCommand" not in args


def test_windows_blocked_setting_is_reported():
    result = SimpleNamespace(returncode=1, stderr=b"Windows notifications are blocked (DisabledForUser).")
    with patch("telegram_notifier.windows.subprocess.run", return_value=result):
        with pytest.raises(RuntimeError, match="DisabledForUser"):
            notify("Test", "Test")
