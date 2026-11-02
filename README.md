# Telegram Notifier

A small Windows application that notifies you when a selected Telegram contact comes online or starts typing in your private chat. Notifications can appear on the desktop, through your own Telegram bot, or both.

## Download and run

Download the Windows ZIP from this repository's Releases page, extract the entire folder, and open **TelegramNotifier.exe**. Python is included. No command window or administrator access is required.

The application is unsigned. Its source and build instructions are available here; check the release checksum before running a downloaded copy.

## Set up

1. On **Account**, enter your API ID and API hash from [my.telegram.org/apps](https://my.telegram.org/apps), plus your phone number with its country code.
2. Click **Connect account**. Enter the login code sent by Telegram and your two-step verification password if requested.
3. On **Monitor**, choose a recent chat or enter an exact `@username`. Select online events, typing events, or both, and click **Start monitoring**.
4. Windows notifications are enabled by default. To add Telegram delivery, create a bot with [/newbot in BotFather](https://t.me/BotFather), paste its token on **Settings**, and press **Start** in the bot's chat using the account you connected here. Save the settings, restart monitoring, and use **Test Telegram**.

**Test Windows** works without signing in. Closing the window leaves the app in the system tray by default. Use its tray menu or **File → Exit** to stop it completely. Only one copy runs at a time.

## Limits

- Online events depend on what Telegram exposes to your account. The app cannot reveal hidden status.
- Typing events cover only the selected person's private conversation with you.
- A contact already online when monitoring starts does not generate an arrival notification.
- The minimum interval applies separately to each event type. Repeated typing updates are grouped into a single burst.
- Sleep and network interruptions can cause missed events. Reconnection is automatic; events from the gap are not replayed.
- Do Not Disturb and Telegram notification settings can suppress notification banners or sounds.
- The app does not read or retain message contents. Activity stays in memory and is cleared on exit.

## Privacy

Every installation uses its own Telegram account credentials. The app has no developer-operated service, telemetry, remote commands, or update downloader. See [PRIVACY.md](PRIVACY.md) for storage, network access, and removal details.

## Run from source

Windows 10/11, 64-bit Python 3.12 or later with Tcl/Tk:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\pythonw run.pyw
```

## Development

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python tools\build.py
```

The portable build is created in `dist/TelegramNotifier`. `pythonw run.pyw --demo` opens a preview using fictional sample data; it does not connect or save credentials.

Licensed under MIT. Bundled third-party components retain their respective licenses. Independent software, not affiliated with Telegram.
