"""Entry point for AG Printers.

Run from the project folder:

    python run.py
"""

import subprocess
import sys
from pathlib import Path

# If PySide6 is not in the current python environment, auto-switch to project's .venv
try:
    import PySide6  # noqa: F401
except ModuleNotFoundError:
    venv_py = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists() and Path(sys.executable).resolve() != venv_py.resolve():
        raise SystemExit(subprocess.call([str(venv_py)] + sys.argv))
    raise

from app.main import run

if __name__ == "__main__":
    raise SystemExit(run())
