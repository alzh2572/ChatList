"""Диалог «О программе»."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from version import __version__

APP_NAME = "ChatList"
APP_DESCRIPTION = (
    "Приложение для отправки одного промта в несколько нейросетей "
    "и сравнения их ответов."
)
APP_DETAILS = (
    "Python 3.11+ · PyQt6 · SQLite · httpx\n"
    "Лицензия: MIT © 2026"
)


class AboutDialog(QDialog):
    def __init__(
        self,
        icon_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"О программе {APP_NAME}")
        self.setFixedSize(420, 280)

        if icon_path is not None and icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel(f"Версия {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(APP_DESCRIPTION)
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)

        details = QLabel(APP_DETAILS)
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details.setStyleSheet("color: palette(mid);")

        layout = QVBoxLayout(self)
        if icon_path is not None and icon_path.is_file():
            icon_label = QLabel()
            pixmap = QPixmap(str(icon_path)).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon_label)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(description)
        layout.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
