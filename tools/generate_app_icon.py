"""Generate assets/care3d.ico from the same vector artwork used by the UI.

Usage: python tools/generate_app_icon.py [output.ico]
Only PyQt6 and the Python standard library are required.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import struct
import sys

# This is an asset generator, so it never needs to create a visible window.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtWidgets import QApplication


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_icon(destination: Path) -> Path:
    """Write a multi-resolution ICO with lossless RGBA PNG payloads."""
    application = QApplication.instance() or QApplication([])
    # Loading just the drawing module avoids importing ui.__init__, which also
    # initializes application-specific overlay and system-tray dependencies.
    spec = importlib.util.spec_from_file_location(
        "care3d_product_icons", PROJECT_ROOT / "ui" / "product_icons.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the Care3D vector artwork")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payloads = []
    for size in ICON_SIZES:
        buffer = QBuffer()
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            raise RuntimeError("Unable to open the image buffer")
        if not module.logo_pixmap(size).save(buffer, "PNG"):
            raise RuntimeError(f"Unable to render the {size}px application icon")
        payloads.append(bytes(buffer.data()))
        buffer.close()

    header = struct.pack("<HHH", 0, 1, len(ICON_SIZES))
    offset = len(header) + 16 * len(ICON_SIZES)
    entries = []
    for size, payload in zip(ICON_SIZES, payloads):
        dimension = size if size < 256 else 0
        entries.append(struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0,
            1, 32, len(payload), offset
        ))
        offset += len(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(header + b"".join(entries) + b"".join(payloads))
    # Retain the QApplication until all pixmaps and buffers have been released.
    assert application is not None
    return destination


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "assets" / "care3d.ico"
    generated = generate_icon(target.resolve())
    print(f"Generated {generated} ({', '.join(map(str, ICON_SIZES))} px)")
