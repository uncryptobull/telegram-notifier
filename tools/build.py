import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "TelegramNotifier.spec", "--noconfirm"], cwd=ROOT, check=True
    )
    target = ROOT / "dist" / "TelegramNotifier"
    for name in ("README.md", "LICENSE", "PRIVACY.md", "CHANGELOG.md"):
        shutil.copyfile(ROOT / name, target / name)
    licenses = target / "licenses"
    licenses.mkdir(exist_ok=True)
    import importlib.metadata

    for name in ("Telethon", "pystray", "Pillow", "pyaes", "pyasn1", "rsa", "six"):
        distribution = importlib.metadata.distribution(name)
        folder = licenses / name
        folder.mkdir(exist_ok=True)
        for file in distribution.files or ():
            if any(part.lower().startswith(("license", "copying", "notice")) for part in file.parts):
                source = distribution.locate_file(file)
                if source.is_file():
                    shutil.copyfile(source, folder / source.name)
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
    print("Release folder:", target)


if __name__ == "__main__":
    main()
