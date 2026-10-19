"""Codex Loop dawn icon shared by the header, window, tray and installer."""
from pathlib import Path
import struct
from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
ICON_PATH = Path(__file__).resolve().parent / "assets" / "codex-loop-dawn.png"

def render_mark(size: int, *, tile: bool = True) -> QPixmap:
    """Scale the selected artwork smoothly for every desktop icon size."""
    pixmap = QPixmap(str(ICON_PATH))
    if pixmap.isNull():
        raise RuntimeError(f"Missing Codex Loop icon: {ICON_PATH}")
    return pixmap.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


def make_app_icon() -> QIcon:
    """Multi-resolution icon for the window, taskbar, and tray."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(render_mark(size))
    return icon


def build_ico_bytes(sizes: tuple[int, ...] = ICON_SIZES) -> bytes:
    """Assemble a real multi-resolution Windows .ico from PNG entries.

    Qt writes only a single image when saving .ico, which leaves Windows to
    downscale one 256 pixel bitmap for the taskbar and tray. PNG compressed
    entries are read by Windows Vista and later and by Inno Setup, so the
    container is written directly instead.
    """
    images: list[tuple[int, bytes]] = []
    for size in sorted(set(sizes)):
        if not 1 <= size <= 256:
            raise ValueError("Windows icon entries must be 1 to 256 pixels.")
        # The QByteArray must outlive the QBuffer writing into it; letting it be
        # a temporary crashes the interpreter.
        storage = QByteArray()
        buffer = QBuffer(storage)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        if not render_mark(size).save(buffer, "PNG"):
            raise RuntimeError(f"Qt could not encode the {size}px icon entry.")
        buffer.close()
        images.append((size, bytes(storage)))

    header = struct.pack("<HHH", 0, 1, len(images))
    directory = b""
    offset = len(header) + 16 * len(images)
    payload = b""
    for size, data in images:
        directory += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,  # 0 means 256 in the ICO directory
            0 if size >= 256 else size,
            0,  # truecolour, so no palette
            0,
            1,  # colour planes
            32,  # bits per pixel
            len(data),
            offset,
        )
        payload += data
        offset += len(data)
    return header + directory + payload
