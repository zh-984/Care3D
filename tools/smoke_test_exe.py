"""Check packaged initialization and graceful exit using isolated settings.

This exercises --smoke-test, which does not display the control panel or overlay.
It verifies packaging/startup, not real mouse input, game compatibility or efficacy.
"""

import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", nargs="?", default="dist/Care3D_v2.exe")
    args = parser.parse_args()
    executable = Path(args.exe).resolve()
    if not executable.is_file():
        parser.error(f"Executable not found: {executable}")
    with tempfile.TemporaryDirectory(prefix="care3d-exe-check-") as temporary:
        environment = dict(os.environ, LOCALAPPDATA=temporary)
        process = subprocess.Popen([str(executable), "--smoke-test"], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # Only terminate the process tree created by this test.
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            raise RuntimeError("Packaged startup timed out") from None
        if returncode:
            raise RuntimeError(f"Executable exited with code {returncode}")
        directory = Path(temporary) / "Care3D"
        log = (directory / "care3d.log").read_text(encoding="utf-8")
        if "UI event loop ready" not in log or "Shutdown complete" not in log:
            raise RuntimeError("Startup or shutdown checkpoint missing")
        if not (directory / "config.json").is_file() or (directory / "care3d.lock").exists():
            raise RuntimeError("Configuration save or instance cleanup failed")
    print("Packaged initialization, configuration save and shutdown passed.")


if __name__ == "__main__":
    main()
