# Security

Do not include API hashes, bot tokens, login codes, phone numbers, session files, or unredacted logs in issues. Use fictional data when reporting a problem.

For vulnerabilities, use this repository's private vulnerability reporting feature when available. Do not disclose working credentials in a public issue. If private reporting is unavailable, request a private reporting channel without publishing exploit details.

Release builds contain no maintainer credentials. Sessions and secrets are stored locally using Windows DPAPI. They remain sensitive even when encrypted. See [PRIVACY.md](PRIVACY.md) for the limits of this protection.

Only the latest release is maintained. Fixes are published as new versions. Download official releases or build from the repository; modified copies are outside this project's control.
