from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "aginti-hardware-console.svg"
ICO_PATH = ASSETS / "aginti-hardware-console.ico"
PNG_PATH = ASSETS / "aginti-hardware-console-512.png"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Could not encode {size}px icon")
    return bytes(buffer.data())


def write_ico(images: list[tuple[int, bytes]]) -> None:
    header_size = 6 + 16 * len(images)
    offset = header_size
    entries = []
    payload = bytearray()
    for size, data in images:
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset)
        )
        payload.extend(data)
        offset += len(data)
    ICO_PATH.write_bytes(struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + payload)


def main() -> None:
    app = QGuiApplication([])
    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {SVG_PATH}")
    images = [(size, render_png(renderer, size)) for size in SIZES]
    write_ico(images)
    PNG_PATH.write_bytes(render_png(renderer, 512))
    app.quit()


if __name__ == "__main__":
    main()
