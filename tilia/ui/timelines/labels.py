from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics

from tilia.settings import settings


def elide_text(text: str, font: QFont, max_width: float) -> str:
    """Return `text` truncated with ellipsis to fit within `max_width` pixels.

    Empty input returns "". A non-positive `max_width` returns "" so a
    label whose container has collapsed renders nothing rather than a stray
    ellipsis.
    """
    if not text or max_width <= 0:
        return ""
    return QFontMetrics(font).elidedText(
        text, Qt.TextElideMode.ElideRight, int(max_width)
    )


def get_label_font(settings_group: str, family: str = "Arial") -> QFont:
    """Return the font set for labels in `settings_group`.

    The group must hold `label_font_size`, `label_bold`, `label_italic` and
    `label_underline`.
    """
    return get_font(settings_group, "label", family)


def get_font(settings_group: str, prefix: str, family: str = "Arial") -> QFont:
    font = QFont(family, settings.get(settings_group, f"{prefix}_font_size"))
    font.setBold(settings.get(settings_group, f"{prefix}_bold"))
    font.setItalic(settings.get(settings_group, f"{prefix}_italic"))
    font.setUnderline(settings.get(settings_group, f"{prefix}_underline"))
    return font
