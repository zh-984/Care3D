"""Check packaged initialization and graceful exit using isolated settings.

This exercises --smoke-test, which does not display the control panel or overlay.
It verifies packaging/startup, not real mouse input, game compatibility or efficacy.
"""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", nargs="?", default="dist/Care3D_v2.exe")
    parser.add_argument("--timeout", type=float, default=60,
                        help="Startup/exit deadline in seconds (default: 60)")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("Timeout must be positive")
    executable = Path(args.exe).resolve()
    if not executable.is_file():
        parser.error(f"Executable not found: {executable}")
    with tempfile.TemporaryDirectory(prefix="care3d-exe-check-") as temporary:
        environment = dict(os.environ, LOCALAPPDATA=temporary)
        directory = Path(temporary) / "Care3D"
        output_path = Path(temporary) / "process-output.log"
        with output_path.open("wb") as output:
            process = subprocess.Popen([str(executable), "--smoke-test"], env=environment,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                returncode = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                # Only terminate the process tree created by this test.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                process.wait(timeout=10)
                returncode = None
        if returncode != 0:
            for label, path in (("Application log", directory / "care3d.log"),
                                ("Process output", output_path)):
                content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "(not created)"
                print(f"{label}:\n{content[-8000:]}", file=sys.stderr)
            if returncode is None:
                raise RuntimeError(f"Packaged startup timed out after {args.timeout:g}s")
            raise RuntimeError(f"Executable exited with code {returncode}")
        log = (directory / "care3d.log").read_text(encoding="utf-8")
        if "UI event loop ready" not in log or "Shutdown complete" not in log:
            raise RuntimeError("Startup or shutdown checkpoint missing")
        if not (directory / "config.json").is_file() or (directory / "care3d.lock").exists():
            raise RuntimeError("Configuration save or instance cleanup failed")
    print("Packaged initialization, configuration save and shutdown passed.")


if __name__ == "__main__":
    main()
