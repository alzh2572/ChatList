"""Диалог AI-ассистента для улучшения промтов."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prompt_assistant import PromptImprovementResult

ADAPTATION_LABELS = {
    "code": "Код",
    "analysis": "Анализ",
    "creative": "Креатив",
}


class PromptAssistantDialog(QDialog):
    def __init__(
        self,
        result: PromptImprovementResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.result = result
        self.selected_text = result.improved
        self._button_group = QButtonGroup(self)

        self.setWindowTitle("Улучшение промта")
        self.resize(760, 620)

        layout = QVBoxLayout(self)

        if result.error:
            layout.addWidget(QLabel(f"Примечание: {result.error}"))

        layout.addWidget(self._labeled_readonly("Исходный промт", result.original))

        options_box = QGroupBox("Варианты промта")
        options_layout = QVBoxLayout(options_box)

        self._add_option(options_layout, "Улучшенный", result.improved, checked=True)
        for index, alternative in enumerate(result.alternatives, start=1):
            self._add_option(options_layout, f"Альтернатива {index}", alternative)

        for key, value in result.adaptations.items():
            label = ADAPTATION_LABELS.get(key, key.capitalize())
            self._add_option(options_layout, f"Адаптация: {label}", value)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(options_box)
        layout.addWidget(scroll)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlainText(self.selected_text)
        self.preview.setMaximumHeight(120)
        layout.addWidget(QLabel("Выбранный вариант:"))
        layout.addWidget(self.preview)

        buttons_row = QHBoxLayout()
        copy_btn = QPushButton("Копировать")
        copy_btn.clicked.connect(self._copy_selected)
        buttons_row.addWidget(copy_btn)
        buttons_row.addStretch()

        dialog_buttons = QDialogButtonBox()
        apply_btn = dialog_buttons.addButton(
            "Подставить в поле ввода",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        close_btn = dialog_buttons.addButton(
            QDialogButtonBox.StandardButton.Close
        )
        apply_btn.clicked.connect(self.accept)
        close_btn.clicked.connect(self.reject)

        layout.addLayout(buttons_row)
        layout.addWidget(dialog_buttons)

    def _labeled_readonly(self, title: str, text: str) -> QWidget:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setMaximumHeight(100)
        layout.addWidget(editor)
        return box

    def _add_option(
        self,
        layout: QVBoxLayout,
        title: str,
        text: str,
        *,
        checked: bool = False,
    ) -> None:
        if not text.strip():
            return

        radio = QRadioButton(title)
        radio.setChecked(checked)
        self._button_group.addButton(radio)
        radio.toggled.connect(
            lambda selected, value=text: self._on_option_selected(selected, value)
        )
        layout.addWidget(radio)

        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setPlainText(text)
        preview.setMaximumHeight(90)
        layout.addWidget(preview)

    def _on_option_selected(self, selected: bool, text: str) -> None:
        if not selected:
            return
        self.selected_text = text
        self.preview.setPlainText(text)

    def _copy_selected(self) -> None:
        QApplication.clipboard().setText(self.selected_text)

    def get_selected_text(self) -> str:
        return self.selected_text
