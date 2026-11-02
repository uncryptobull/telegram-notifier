import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ssl_source = Path(sys.base_prefix) / "Lib" / "ssl.py"
    if ssl_source.exists() and "cafile=os.path.join(os.path.dirname(__file__)" in ssl_source.read_text(
        encoding="utf-8"
    ):
        raise SystemExit("Build with a standard Python installation, not a customized runtime.")
    for key, folder in [("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")]:
        library = Path(sys.base_prefix) / "tcl" / folder
        if os.name == "nt" and library.exists():
            os.environ[key] = "//?/" + library.as_posix()
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "TelegramNotifier.spec", "--noconfirm", "--clean"],
        cwd=ROOT,
        check=True,
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
