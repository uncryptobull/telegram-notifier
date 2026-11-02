# Privacy and account access

Telegram Notifier connects directly to Telegram using credentials supplied by the person running it. The maintainer's credentials are not distributed.

## Local storage

If **Remember this account** is enabled, API details, the session, optional bot token, and settings are encrypted with Windows user-level DPAPI and saved to `%LOCALAPPDATA%/TelegramNotifier/profile.bin`. Codes and two-step passwords are never saved. If saving fails, the app retains the session in memory until exit and reports the failure.

Disable remembering and save the settings to remove the current profile from disk. The current connection can continue in memory. Activity is not written to a log file.

When upgrading from the original folder-based version, the app can read its encrypted `settings.bin` once. That older file is left intact to preserve the original installation. Delete it yourself if retiring that installation. The marker `profile.initialized` prevents the new app from re-importing it after sign-out.

DPAPI protects stored data from straightforward copying to another Windows account. It does not protect against software running as you, an unlocked account, or administrator-level compromise. A Telegram session grants access to the connected account; keep it private.

## Network access

The app connects to Telegram's MTProto infrastructure for authentication, recent chat selection, and status/typing events. Optional bot delivery uses `api.telegram.org` over HTTPS. Telegram receives the notifications you choose to send through that bot. There is no inbound listener, telemetry service, or remote control interface.

The API, BotFather, and bot links open Telegram websites when clicked. No update checks run automatically.

## Notifications

Names can be hidden in status and notification messages using **Hide contact names**. Contact selection and Account settings may still contain identifying information. Use `--demo` for public screenshots.

The first Windows notification creates a per-user Start menu shortcut so Windows can identify the sender. Removing the portable folder does not remove that shortcut or the encrypted profile.

## Sign out and remove

Stop monitoring, open **Account**, and choose **Sign out**. Successful sign-out revokes this app's Telegram session and clears the current local profile. If the internet is unavailable, revoke the session in Telegram **Settings → Devices** and remove the profile file manually. Legacy profiles require separate removal as described above.

To uninstall, exit through the tray menu, remove the portable folder, remove the **Telegram Notifier** Start menu shortcut, and remove the app's local data directory. Bot tokens can be revoked through BotFather.
