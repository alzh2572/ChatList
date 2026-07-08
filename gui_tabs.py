"""Вкладки управления: модели, промты, история, настройки."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import db
from export_utils import default_export_path, export_to_json, export_to_markdown
from table_utils import connect_search, setup_sortable_table


class ModelEditDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        name: str = "",
        api_url: str = "https://openrouter.ai/api/v1/chat/completions",
        api_id: str = "OPENROUTER_API_KEY",
        is_active: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Модель")
        self.resize(520, 220)

        self.name_input = QLineEdit(name)
        self.url_input = QLineEdit(api_url)
        self.api_id_input = QLineEdit(api_id)
        self.active_checkbox = QCheckBox("Активна")
        self.active_checkbox.setChecked(is_active)

        form = QFormLayout()
        form.addRow("Имя модели:", self.name_input)
        form.addRow("API URL:", self.url_input)
        form.addRow("Переменная ключа (.env):", self.api_id_input)
        form.addRow("", self.active_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, object]:
        return {
            "name": self.name_input.text().strip(),
            "api_url": self.url_input.text().strip(),
            "api_id": self.api_id_input.text().strip(),
            "is_active": self.active_checkbox.isChecked(),
        }


class PromptEditDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        prompt: str = "",
        tags: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Промт")
        self.resize(520, 320)

        self.prompt_input = QPlainTextEdit(prompt)
        self.tags_input = QLineEdit(tags)

        form = QFormLayout()
        form.addRow("Текст:", self.prompt_input)
        form.addRow("Теги:", self.tags_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {
            "prompt": self.prompt_input.toPlainText().strip(),
            "tags": self.tags_input.text().strip(),
        }


class ModelsTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[dict] = []

        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени, URL или переменной ключа...")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "API URL", "Ключ (.env)", "Активна"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        setup_sortable_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        edit_btn = QPushButton("Изменить")
        toggle_btn = QPushButton("Вкл/Выкл")
        delete_btn = QPushButton("Удалить")
        refresh_btn = QPushButton("Обновить")

        add_btn.clicked.connect(self._on_add)
        edit_btn.clicked.connect(self._on_edit)
        toggle_btn.clicked.connect(self._on_toggle)
        delete_btn.clicked.connect(self._on_delete)
        refresh_btn.clicked.connect(self.reload)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(toggle_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(refresh_btn)

        layout.addWidget(QLabel("Модели нейросетей"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        connect_search(self.table, self.search_input, [1, 2, 3])
        self.reload()

    def reload(self) -> None:
        self.table.setSortingEnabled(False)
        self._records = db.list_models()
        self.table.setRowCount(len(self._records))

        for row_index, record in enumerate(self._records):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(record["id"])))
            self.table.setItem(row_index, 1, QTableWidgetItem(record["name"]))
            self.table.setItem(row_index, 2, QTableWidgetItem(record["api_url"]))
            self.table.setItem(row_index, 3, QTableWidgetItem(record["api_id"]))
            active_item = QTableWidgetItem("Да" if record["is_active"] else "Нет")
            self.table.setItem(row_index, 4, active_item)

        self.table.setSortingEnabled(True)

    def _selected_record(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return None
        id_item = self.table.item(row, 0)
        if id_item is None:
            return None
        model_id = int(id_item.text())
        return db.get_model(model_id)

    def _on_add(self) -> None:
        dialog = ModelEditDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["name"] or not values["api_url"] or not values["api_id"]:
            QMessageBox.warning(self, "ChatList", "Заполните все поля модели.")
            return
        try:
            db.create_model(
                str(values["name"]),
                str(values["api_url"]),
                str(values["api_id"]),
                bool(values["is_active"]),
            )
        except Exception as exc:
            QMessageBox.critical(self, "ChatList", f"Не удалось добавить модель:\n{exc}")
            return
        self.reload()
        self.changed.emit()

    def _on_edit(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите модель.")
            return

        dialog = ModelEditDialog(
            self,
            name=record["name"],
            api_url=record["api_url"],
            api_id=record["api_id"],
            is_active=bool(record["is_active"]),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["name"] or not values["api_url"] or not values["api_id"]:
            QMessageBox.warning(self, "ChatList", "Заполните все поля модели.")
            return
        try:
            db.update_model(
                int(record["id"]),
                name=str(values["name"]),
                api_url=str(values["api_url"]),
                api_id=str(values["api_id"]),
                is_active=bool(values["is_active"]),
            )
        except Exception as exc:
            QMessageBox.critical(self, "ChatList", f"Не удалось изменить модель:\n{exc}")
            return
        self.reload()
        self.changed.emit()

    def _on_toggle(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите модель.")
            return
        db.update_model(int(record["id"]), is_active=not bool(record["is_active"]))
        self.reload()
        self.changed.emit()

    def _on_delete(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите модель.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            f"Удалить модель «{record['name']}»?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            db.delete_model(int(record["id"]))
        except Exception as exc:
            QMessageBox.critical(self, "ChatList", f"Не удалось удалить модель:\n{exc}")
            return
        self.reload()
        self.changed.emit()


class PromptsTab(QWidget):
    use_prompt = pyqtSignal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[dict] = []

        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по тексту или тегам...")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Теги"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        setup_sortable_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        buttons = QHBoxLayout()
        use_btn = QPushButton("Использовать")
        edit_btn = QPushButton("Изменить")
        delete_btn = QPushButton("Удалить")
        refresh_btn = QPushButton("Обновить")

        use_btn.clicked.connect(self._on_use)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)
        refresh_btn.clicked.connect(self.reload)

        buttons.addWidget(use_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(refresh_btn)

        layout.addWidget(QLabel("Сохранённые промты"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        connect_search(self.table, self.search_input, [1, 2, 3])
        self.reload()

    def reload(self) -> None:
        self.table.setSortingEnabled(False)
        self._records = db.list_prompts()
        self.table.setRowCount(len(self._records))

        for row_index, record in enumerate(self._records):
            preview = record["prompt"].replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:117] + "..."

            self.table.setItem(row_index, 0, QTableWidgetItem(str(record["id"])))
            self.table.setItem(row_index, 1, QTableWidgetItem(record["created_at"][:19]))
            self.table.setItem(row_index, 2, QTableWidgetItem(preview))
            self.table.setItem(row_index, 3, QTableWidgetItem(record.get("tags") or ""))

        self.table.setSortingEnabled(True)

    def _selected_record(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        if id_item is None:
            return None
        return db.get_prompt(int(id_item.text()))

    def _on_use(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите промт.")
            return
        self.use_prompt.emit(int(record["id"]), record["prompt"])

    def _on_edit(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите промт.")
            return

        dialog = PromptEditDialog(
            self,
            prompt=record["prompt"],
            tags=record.get("tags") or "",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["prompt"]:
            QMessageBox.warning(self, "ChatList", "Текст промта не может быть пустым.")
            return
        db.update_prompt(
            int(record["id"]),
            prompt=values["prompt"],
            tags=values["tags"] or None,
        )
        self.reload()

    def _on_delete(self) -> None:
        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "ChatList", "Выберите промт.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            "Удалить выбранный промт и связанные результаты?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        db.delete_prompt(int(record["id"]))
        self.reload()


class HistoryTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._records: list[dict] = []

        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по промту, модели или ответу...")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Промт", "Модель", "Ответ"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        setup_sortable_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        buttons = QHBoxLayout()
        export_md_btn = QPushButton("Экспорт Markdown")
        export_json_btn = QPushButton("Экспорт JSON")
        delete_btn = QPushButton("Удалить")
        refresh_btn = QPushButton("Обновить")

        export_md_btn.clicked.connect(lambda: self._export("md"))
        export_json_btn.clicked.connect(lambda: self._export("json"))
        delete_btn.clicked.connect(self._on_delete)
        refresh_btn.clicked.connect(self.reload)

        buttons.addWidget(export_md_btn)
        buttons.addWidget(export_json_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(refresh_btn)

        layout.addWidget(QLabel("История сохранённых результатов"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

        connect_search(self.table, self.search_input, [1, 2, 3, 4])
        self.reload()

    def reload(self) -> None:
        self.table.setSortingEnabled(False)
        self._records = db.list_results()
        self.table.setRowCount(len(self._records))

        for row_index, record in enumerate(self._records):
            prompt_preview = record["prompt"].replace("\n", " ")
            if len(prompt_preview) > 80:
                prompt_preview = prompt_preview[:77] + "..."
            response_preview = record["response"].replace("\n", " ")
            if len(response_preview) > 120:
                response_preview = response_preview[:117] + "..."

            self.table.setItem(row_index, 0, QTableWidgetItem(str(record["id"])))
            self.table.setItem(row_index, 1, QTableWidgetItem(record["created_at"][:19]))
            self.table.setItem(row_index, 2, QTableWidgetItem(prompt_preview))
            self.table.setItem(row_index, 3, QTableWidgetItem(record["model_name"]))
            self.table.setItem(row_index, 4, QTableWidgetItem(response_preview))

        self.table.setSortingEnabled(True)

    def _selected_records(self) -> list[dict]:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        selected: list[dict] = []
        for row in rows:
            id_item = self.table.item(row, 0)
            if id_item is None:
                continue
            for record in self._records:
                if int(record["id"]) == int(id_item.text()):
                    selected.append(record)
                    break
        return selected

    def _export(self, fmt: str) -> None:
        items = self._selected_records() or self._records
        if not items:
            QMessageBox.information(self, "ChatList", "Нет данных для экспорта.")
            return

        if fmt == "md":
            default_path = str(default_export_path("md"))
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт Markdown", default_path, "Markdown (*.md)"
            )
            if not path:
                return
            export_to_markdown(items, path)
        else:
            default_path = str(default_export_path("json"))
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт JSON", default_path, "JSON (*.json)"
            )
            if not path:
                return
            export_to_json(items, path)

        QMessageBox.information(self, "ChatList", f"Экспорт выполнен:\n{path}")

    def _on_delete(self) -> None:
        items = self._selected_records()
        if not items:
            QMessageBox.information(self, "ChatList", "Выберите записи для удаления.")
            return
        answer = QMessageBox.question(
            self,
            "ChatList",
            f"Удалить выбранные записи ({len(items)})?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for item in items:
            db.delete_result(int(item["id"]))
        self.reload()


class SettingsTab(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(5, 600)
        self.theme_input = QLineEdit()
        self.assistant_model_combo = QComboBox()
        self.db_path_label = QLabel()

        form = QFormLayout()
        form.addRow("Таймаут запросов (сек):", self.timeout_input)
        form.addRow("Тема (light/dark):", self.theme_input)
        form.addRow("Модель для улучшения промта:", self.assistant_model_combo)
        form.addRow("Файл базы данных:", self.db_path_label)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self._on_save)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Настройки программы"))
        layout.addLayout(form)
        layout.addWidget(save_btn)
        layout.addStretch()

        self.reload()

    def reload(self) -> None:
        self.timeout_input.setValue(
            int(db.get_setting("request_timeout", "60") or "60")
        )
        self.theme_input.setText(db.get_setting("theme", "light") or "light")
        self.db_path_label.setText(str(db.get_db_path()))

        selected_id = db.get_setting("assistant_model_id")
        self.assistant_model_combo.clear()
        selected_index = 0
        for index, model in enumerate(db.list_active_models()):
            self.assistant_model_combo.addItem(model["name"], model["id"])
            if selected_id and str(model["id"]) == str(selected_id):
                selected_index = index
        if self.assistant_model_combo.count() > 0:
            self.assistant_model_combo.setCurrentIndex(selected_index)

    def _on_save(self) -> None:
        db.set_setting("request_timeout", str(self.timeout_input.value()))
        theme = self.theme_input.text().strip() or "light"
        db.set_setting("theme", theme)
        if self.assistant_model_combo.currentData() is not None:
            db.set_setting(
                "assistant_model_id",
                str(self.assistant_model_combo.currentData()),
            )
        QMessageBox.information(self, "ChatList", "Настройки сохранены.")
        self.settings_saved.emit()
