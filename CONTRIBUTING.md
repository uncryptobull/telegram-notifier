# Contributing

Bug fixes, documentation corrections, and focused improvements are welcome. For a larger feature, open an issue describing the use case before starting work.

## Report a problem

Include the app version, Windows version, steps to reproduce the problem, and what you expected to happen. Check the existing issues first.

Use fictional contact names and remove personal details from screenshots. Never attach API hashes, bot tokens, phone numbers, login codes, Telegram sessions, or saved account files. Report vulnerabilities using [SECURITY.md](SECURITY.md).

## Set up a development environment

Use Windows 10 or 11 and a standard 64-bit Python installation, version 3.12 or later, with Tcl/Tk available.

```powershell
git clone https://github.com/uncryptobull/telegram-notifier.git
cd telegram-notifier
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\pythonw run.pyw --demo
```

Demo mode uses fictional data without connecting to Telegram or saving credentials. Prefer it for interface work and screenshots.

## Submit a change

Create a branch for one focused change. Explain the problem, the resulting behavior, and how you checked it in the pull request. Add a regression test when it helps verify a bug fix; documentation changes do not need tests.

Run these checks before submitting code:

```powershell
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pytest
.venv\Scripts\python tools\check_source.py
.venv\Scripts\python -m pip_audit -r requirements.txt
```

The Windows workflow also builds the application. To check a packaging change locally, run `.venv\Scripts\python tools\build.py`; the result is in `dist/TelegramNotifier`.

Keep credentials, account data, generated builds, and local environment files out of commits. Before pushing, inspect `git diff --cached` and confirm it contains only the intended source changes. Use GitHub's noreply email for commits if you want to keep your email private.
