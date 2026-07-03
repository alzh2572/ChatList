"""Просмотр ответа в форматированном Markdown."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout


def format_response_markdown(model_name: str, prompt: str, response: str) -> str:
    prompt_block = prompt.strip() or "—"
    return (
        f"## {model_name}\n\n"
        f"### Промт\n\n"
        f"{prompt_block}\n\n"
        f"### Ответ\n\n"
        f"{response.strip()}"
    )


class MarkdownViewDialog(QDialog):
    def __init__(
        self,
        title: str,
        markdown: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)

        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setMarkdown(markdown)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.viewer)
        layout.addWidget(buttons)
