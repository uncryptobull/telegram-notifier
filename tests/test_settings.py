import json
from dataclasses import replace

import pytest

from telegram_notifier.settings import ProfileStore, Settings


def valid():
    return Settings(api_id="100", api_hash="a" * 32, target="@example", session="sample-session")


def test_windows_only_needs_no_bot():
    valid().validate()


def test_bot_required_only_when_enabled():
    with pytest.raises(ValueError, match="bot token"):
        replace(valid(), telegram=True).validate()


def test_connect_does_not_require_contact_or_delivery():
    replace(valid(), target="", desktop=False).validate(connecting=True)


@pytest.mark.parametrize(
    "changes",
    [
        {"api_hash": "bad"},
        {"api_id": "-1"},
        {"target": ""},
        {"cooldown": 0},
        {"typing": False, "online": False},
        {"desktop": False, "telegram": False},
    ],
)
def test_invalid_watch_settings(changes):
    with pytest.raises(ValueError):
        replace(valid(), **changes).validate()


def test_legacy_read_is_not_reimported_after_clear(tmp_path, monkeypatch):
    monkeypatch.setattr("telegram_notifier.settings.load", lambda path: {"api_id": 100, "session": "sample"})
    (tmp_path / "settings.bin").write_bytes(b"legacy")
    store = ProfileStore(tmp_path)
    assert store.read().session == "sample"
    store.clear()
    assert not store.read().session
    assert (tmp_path / "settings.bin").exists()


def test_no_phone_or_password_in_persisted_settings(tmp_path, monkeypatch):
    values = []
    monkeypatch.setattr("telegram_notifier.settings.save", lambda path, data: values.append(data))
    store = ProfileStore(tmp_path)
    store.write(valid())
    assert values
    assert all(key not in values[0] for key in ("phone", "password", "code"))


def test_remember_off_removes_profile(tmp_path):
    (tmp_path / "profile.bin").write_bytes(b"old")
    store = ProfileStore(tmp_path)
    store.write(replace(valid(), remember=False))
    assert not store.path.exists()
    assert store.marker.exists()


def test_unknown_settings_are_ignored():
    cfg = Settings.from_dict(json.loads('{"api_id":100,"password":"unused"}'))
    assert cfg.api_id == 100
    assert not hasattr(cfg, "password")
