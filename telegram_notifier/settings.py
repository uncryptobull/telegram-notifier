import os
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .windows import load, save


@dataclass
class Settings:
    api_id: str = ""
    api_hash: str = ""
    session: str = ""
    target: str = ""
    target_name: str = ""
    online: bool = True
    typing: bool = True
    desktop: bool = True
    telegram: bool = False
    bot_token: str = ""
    cooldown: int = 15
    remember: bool = True
    close_to_tray: bool = True
    private_preview: bool = False

    @classmethod
    def from_dict(cls, data):
        allowed = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def validate(self, phone="", connecting=False):
        if not str(self.api_id).isdecimal() or int(self.api_id) <= 0:
            raise ValueError("Enter the numeric API ID from my.telegram.org/apps.")
        if not re.fullmatch(r"[a-fA-F0-9]{32}", self.api_hash):
            raise ValueError("Enter the 32-character API hash from my.telegram.org/apps.")
        if not self.session and not re.fullmatch(r"\+\d{7,15}", phone):
            raise ValueError("Enter your phone number with + and the country code.")
        if connecting:
            return
        if not self.target.strip():
            raise ValueError("Select a recent chat or enter an exact @username.")
        if not (self.online or self.typing):
            raise ValueError("Choose at least one event to notify you about.")
        if not (self.desktop or self.telegram):
            raise ValueError("Choose Windows notifications, Telegram delivery, or both.")
        if self.telegram and not re.fullmatch(r"\d+:[A-Za-z0-9_-]{20,}", self.bot_token):
            raise ValueError("Enter the bot token from BotFather, or turn off Telegram delivery.")
        if not 5 <= self.cooldown <= 300:
            raise ValueError("Choose an alert interval between 5 and 300 seconds.")


class ProfileStore:
    def __init__(self, directory=None):
        self.directory = Path(directory or Path(os.environ["LOCALAPPDATA"]) / "TelegramNotifier")
        self.path = self.directory / "profile.bin"
        self.marker = self.directory / "profile.initialized"

    def read(self):
        if self.path.exists():
            return Settings.from_dict(load(self.path))
        legacy = self.directory / "settings.bin"
        if not self.marker.exists() and legacy.exists():
            return Settings.from_dict(load(legacy))
        return Settings()

    def write(self, settings):
        self.directory.mkdir(parents=True, exist_ok=True)
        if settings.remember:
            save(self.path, asdict(settings))
        else:
            self.path.unlink(missing_ok=True)
        self.marker.touch()

    def clear(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        self.marker.touch()
