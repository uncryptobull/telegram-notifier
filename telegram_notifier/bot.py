"""Outbound-only Bot API delivery. No webhook or update polling required."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class BotDeliveryError(Exception):
    pass


class AlertBot:
    def __init__(self, token):
        self.token = token

    def call(self, method, payload):
        request = Request(
            "https://api.telegram.org/bot" + self.token + "/" + method,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                result = json.load(response)
        except HTTPError as exc:
            if exc.code == 403:
                raise BotDeliveryError(
                    "Open the alert bot in Telegram and press Start, then test again."
                ) from None
            if exc.code == 429:
                raise BotDeliveryError(
                    "Telegram limited bot delivery. This alert was skipped; try again later."
                ) from None
            raise BotDeliveryError(
                "Check the bot token and press Start in its chat before testing."
            ) from None
        except Exception:
            raise BotDeliveryError("Could not reach the alert bot. Check your connection.") from None
        if not result.get("ok"):
            raise BotDeliveryError("The alert bot rejected this request. Check its token and chat.")
        return result["result"]

    def identity(self):
        return self.call("getMe", {})["username"]

    def send(self, user_id, title, text):
        return self.call("sendMessage", {"chat_id": user_id, "text": title + "\n" + text})
