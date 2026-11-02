import os
import sys
from pathlib import Path

for key, folder in [("TCL_LIBRARY", "tcl8.6"), ("TK_LIBRARY", "tk8.6")]:
    library = Path(sys.base_prefix) / "tcl" / folder
    if os.name == "nt" and library.exists():
        os.environ[key] = "//?/" + library.as_posix()
