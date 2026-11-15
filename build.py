"""Build the single-file Windows executable."""
from pathlib import Path
import os
import subprocess
import sys
import PyQt6

def build():
    root = Path(__file__).resolve().parent
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "Care3D_v2.spec",
    ]
    # Keep unrelated native SDKs/codecs off DLL discovery paths during packaging.
    environment = os.environ.copy()
    windows = Path(environment.get("SystemRoot", "C:/Windows"))
    qt_bin = Path(PyQt6.__file__).parent / "Qt6" / "bin"
    environment["PATH"] = os.pathsep.join(map(str, (Path(sys.executable).parent, qt_bin,
                                                    windows / "System32", windows)))
    subprocess.run(command, cwd=root, check=True, env=environment)
    print(f"EXE: {root / 'dist' / 'Care3D_v2.exe'}")

if __name__ == "__main__":
    build()
