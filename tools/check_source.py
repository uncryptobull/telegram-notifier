import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "local user path": re.compile(rb"(?i)[a-z]:[\\/]+Users[\\/]+[^\\/\s]+"),
    "phone number": re.compile(rb"(?<!\w)\+\d{10,15}(?!\d)"),
    "bot token": re.compile(rb"\b\d{6,12}:[A-Za-z0-9_-]{25,}\b"),
}


def main():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    failures = []
    for name in result.stdout.decode().split("\0"):
        if not name:
            continue
        path = ROOT / name
        if path.suffix.lower() in {".session", ".bin", ".lnk", ".pyc", ".log", ".exe"} or path.name == ".env":
            failures.append(f"{name}: private or generated file type")
        if path.suffix.lower() in {".py", ".pyw", ".ps1", ".md", ".txt", ".toml", ".yml"}:
            contents = path.read_bytes()
            for label, pattern in PATTERNS.items():
                if pattern.search(contents):
                    failures.append(f"{name}: possible {label}")
    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print("Tracked source check passed.")


if __name__ == "__main__":
    main()
