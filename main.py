import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import db
from export_utils import default_export_path, export_to_json, export_to_markdown
from gui_tabs import HistoryTab, ModelsTab, PromptsTab, SettingsTab
from log_utils import get_logger
from markdown_viewer import MarkdownViewDialog, format_response_markdown
from models import get_active_models, get_assistant_model
from network import ModelResponse, send_prompt_to_all_models
from prompt_assistant import PromptImprovementResult, improve_prompt
from prompt_assistant_dialog import PromptAssistantDialog
from session import QuerySession
from table_utils import connect_search, resize_table_rows, setup_multiline_table

logger = get_logger()


class ImprovePromptWorker(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def run(self) -> None:
        try:
            model = get_assistant_model()
            if model is None:
                self.failed.emit(
                    "Нет активной модели для ассистента. Настройте её на вкладке «Настройки»."
                )
                return
            logger.info("Улучшение промта через модель %s", model.name)
            result = improve_prompt(self.prompt, model)
            if result.error and not result.improved:
                self.failed.emit(result.error)
                return
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("Ошибка при улучшении промта")
            self.failed.emit(str(exc))


class RequestWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def run(self) -> None:
        try:
            models = get_active_models()
            logger.info("Отправка промта в %d активных моделей", len(models))
            responses = send_prompt_to_all_models(self.prompt, models)
            self.finished.emit(responses)
        except Exception as exc:
            logger.exception("Ошибка при отправке промта")
            self.failed.emit(str(exc))


class QueryTab(QWidget):
    saved = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = QuerySession()
        self.worker: RequestWorker | None = None
        self.improve_worker: ImprovePromptWorker | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_prompt_section())
        layout.addWidget(self._build_results_section())
        layout.addWidget(self._build_actions_section())

    def _build_prompt_section(self) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)

        self.prompt_combo = QComboBox()
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)

        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Введите текст запроса...")
        self.prompt_input.setMaximumHeight(120)

        send_row = QHBoxLayout()
        self.improve_button = QPushButton("Улучшить промт")
        self.improve_button.clicked.connect(self._on_improve_prompt)
        self.improve_button.setEnabled(False)
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self._on_send)
        self.prompt_input.textChanged.connect(self._update_prompt_buttons)
        send_row.addStretch()
        send_row.addWidget(self.improve_button)
        send_row.addWidget(self.send_button)

        section_layout.addWidget(QLabel("Сохранённые промты:"))
        section_layout.addWidget(self.prompt_combo)
        section_layout.addWidget(QLabel("Промт:"))
        section_layout.addWidget(self.prompt_input)
        section_layout.addLayout(send_row)
        return section

    def _build_results_section(self) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)

        self.results_search = QLineEdit()
        self.results_search.setPlaceholderText("Поиск по модели или ответу...")

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(2, 90)
        self.results_table.setSortingEnabled(False)
        self.results_table.setAlternatingRowColors(True)
        setup_multiline_table(self.results_table)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.itemSelectionChanged.connect(self._update_action_buttons)
        self.results_table.cellDoubleClicked.connect(self._on_open_response)
        connect_search(self.results_table, self.results_search, [0, 1])

        section_layout.addWidget(QLabel("Результаты:"))
        section_layout.addWidget(self.results_search)
        section_layout.addWidget(self.progress)
        section_layout.addWidget(self.results_table)
        return section

    def _build_actions_section(self) -> QWidget:
        section = QWidget()
        row = QHBoxLayout(section)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self._on_save)
        self.save_button.setEnabled(False)

        self.export_md_button = QPushButton("Экспорт MD")
        self.export_md_button.clicked.connect(lambda: self._export_results("md"))
        self.export_md_button.setEnabled(False)

        self.export_json_button = QPushButton("Экспорт JSON")
        self.export_json_button.clicked.connect(lambda: self._export_results("json"))
        self.export_json_button.setEnabled(False)

        self.open_button = QPushButton("Открыть")
        self.open_button.clicked.connect(self._on_open_response)
        self.open_button.setEnabled(False)

        self.new_button = QPushButton("Новый запрос")
        self.new_button.clicked.connect(self._on_new_query)

        row.addWidget(self.save_button)
        row.addWidget(self.open_button)
        row.addWidget(self.export_md_button)
        row.addWidget(self.export_json_button)
        row.addWidget(self.new_button)
        row.addStretch()
        return section

    def load_saved_prompts(self) -> None:
        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— новый промт —", None)

        for item in db.list_prompts():
            preview = item["prompt"].replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            label = f"{item['created_at'][:10]} — {preview}"
            self.prompt_combo.addItem(label, item["id"])

        self.prompt_combo.blockSignals(False)

    def select_prompt(self, prompt_id: int, prompt_text: str) -> None:
        self.prompt_input.setPlainText(prompt_text)
        for i in range(self.prompt_combo.count()):
            if self.prompt_combo.itemData(i) == prompt_id:
                self.prompt_combo.setCurrentIndex(i)
                break

    def _on_prompt_selected(self, index: int) -> None:
        prompt_id = self.prompt_combo.itemData(index)
        if prompt_id is None:
            return
        record = db.get_prompt(int(prompt_id))
        if record:
            self.prompt_input.setPlainText(record["prompt"])

    def _update_prompt_buttons(self) -> None:
        has_text = bool(self.prompt_input.toPlainText().strip())
        loading = self.progress.isVisible()
        self.improve_button.setEnabled(has_text and not loading)
        self.send_button.setEnabled(not loading)

    def _on_improve_prompt(self) -> None:
        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return

        if get_assistant_model() is None:
            QMessageBox.warning(
                self,
                "ChatList",
                "Нет модели для улучшения промта. Выберите модель на вкладке «Настройки».",
            )
            return

        self._set_loading(True)
        self.improve_worker = ImprovePromptWorker(prompt_text)
        self.improve_worker.finished.connect(self._on_improve_finished)
        self.improve_worker.failed.connect(self._on_improve_failed)
        self.improve_worker.start()

    def _on_improve_finished(self, result: PromptImprovementResult) -> None:
        self._set_loading(False)
        dialog = PromptAssistantDialog(result, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.prompt_input.setPlainText(dialog.get_selected_text())

    def _on_improve_failed(self, message: str) -> None:
        self._set_loading(False)
        QMessageBox.critical(self, "ChatList", f"Не удалось улучшить промт:\n{message}")

    def _on_send(self) -> None:
        prompt_text = self.prompt_input.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "ChatList", "Введите текст промта.")
            return

        active_models = get_active_models()
        if not active_models:
            QMessageBox.warning(
                self,
                "ChatList",
                "Нет активных моделей. Добавьте или включите модели на вкладке «Модели».",
            )
            return

        combo_index = self.prompt_combo.currentIndex()
        prompt_id = self.prompt_combo.itemData(combo_index)
        if prompt_id is None:
            prompt_id = db.create_prompt(prompt_text)
            self.load_saved_prompts()
            for i in range(self.prompt_combo.count()):
                if self.prompt_combo.itemData(i) == prompt_id:
                    self.prompt_combo.setCurrentIndex(i)
                    break

        self.session.start_new_prompt(prompt_text, int(prompt_id))
        self._clear_results_table()
        self._set_loading(True)

        self.worker = RequestWorker(prompt_text)
        self.worker.finished.connect(self._on_request_finished)
        self.worker.failed.connect(self._on_request_failed)
        self.worker.start()

    def _on_request_finished(self, responses: list[ModelResponse]) -> None:
        self._set_loading(False)
        self.session.set_results(responses)
        self._populate_results_table()

        errors = [r.error for r in responses if r.error]
        if errors:
            QMessageBox.warning(
                self,
                "ChatList",
                f"Часть запросов завершилась с ошибкой ({len(errors)} из {len(responses)}).\n"
                "Подробности — в таблице результатов.",
            )

    def _on_request_failed(self, message: str) -> None:
        self._set_loading(False)
        QMessageBox.critical(self, "ChatList", f"Не удалось выполнить запрос:\n{message}")

    def _populate_results_table(self) -> None:
        self.results_table.clearContents()
        self.results_table.setRowCount(len(self.session.rows))

        for row_index, row in enumerate(self.session.rows):
            model_item = QTableWidgetItem(row.model_name)
            response_item = QTableWidgetItem(row.response)
            response_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            response_item.setToolTip(row.response)
            if row.error:
                response_item.setForeground(Qt.GlobalColor.red)

            self.results_table.setItem(row_index, 0, model_item)
            self.results_table.setItem(row_index, 1, response_item)
            self.results_table.setCellWidget(
                row_index,
                2,
                self._create_select_checkbox(row_index, row.selected),
            )

        resize_table_rows(self.results_table)
        self._update_action_buttons()

    def _create_select_checkbox(self, row_index: int, checked: bool) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(
            lambda _state, index=row_index, cb=checkbox: self._on_checkbox_changed(
                index, cb.isChecked()
            )
        )
        layout.addWidget(
            checkbox,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        layout.addStretch(1)
        return container

    def _on_checkbox_changed(self, row_index: int, checked: bool) -> None:
        self.session.set_selected(row_index, checked)

    def _on_open_response(self, row: int = -1, _column: int = -1) -> None:
        if row < 0:
            row = self.results_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "ChatList", "Выберите строку с ответом.")
            return

        model_item = self.results_table.item(row, 0)
        response_item = self.results_table.item(row, 1)
        if model_item is None or response_item is None:
            return

        model_name = model_item.text()
        response = response_item.text()
        markdown = format_response_markdown(
            model_name,
            self.session.prompt_text,
            response,
        )
        dialog = MarkdownViewDialog(f"Ответ — {model_name}", markdown, self)
        dialog.exec()

    def _collect_export_items(self) -> list[dict]:
        selected = self.session.get_selected_rows()
        rows = selected or self.session.rows
        return [
            {
                "prompt": self.session.prompt_text,
                "model_name": row.model_name,
                "response": row.response,
            }
            for row in rows
        ]

    def _export_results(self, fmt: str) -> None:
        items = self._collect_export_items()
        if not items:
            QMessageBox.information(self, "ChatList", "Нет результатов для экспорта.")
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

    def _on_save(self) -> None:
        if self.session.prompt_id is None:
            QMessageBox.warning(self, "ChatList", "Нет активного промта для сохранения.")
            return

        selected = self.session.get_selected_rows()
        if not selected:
            QMessageBox.information(self, "ChatList", "Отметьте хотя бы один результат.")
            return

        items = [
            (row.model_id, row.response)
            for row in selected
            if row.error is None
        ]
        skipped = len(selected) - len(items)

        if not items:
            QMessageBox.warning(
                self,
                "ChatList",
                "Среди выбранных строк нет успешных ответов для сохранения.",
            )
            return

        db.save_results_batch(self.session.prompt_id, items)
        logger.info("Сохранено %d результатов для промта %s", len(items), self.session.prompt_id)
        self.session.clear()
        self._clear_results_table()
        self.saved.emit()

        message = f"Сохранено результатов: {len(items)}."
        if skipped:
            message += f"\nПропущено строк с ошибками: {skipped}."
        QMessageBox.information(self, "ChatList", message)

    def _on_new_query(self) -> None:
        self.prompt_input.clear()
        self.prompt_combo.setCurrentIndex(0)
        self.session.clear()
        self._clear_results_table()

    def _clear_results_table(self) -> None:
        self.results_table.clearContents()
        self.results_table.setRowCount(0)
        self._update_action_buttons()

    def _set_loading(self, loading: bool) -> None:
        self.progress.setVisible(loading)
        self.new_button.setEnabled(not loading)
        if loading:
            self.save_button.setEnabled(False)
            self.open_button.setEnabled(False)
            self.export_md_button.setEnabled(False)
            self.export_json_button.setEnabled(False)
            self.improve_button.setEnabled(False)
            self.send_button.setEnabled(False)
        else:
            self._update_prompt_buttons()
            self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        has_results = self.session.has_results()
        has_selection = self.results_table.currentRow() >= 0
        self.save_button.setEnabled(has_results)
        self.open_button.setEnabled(has_results and has_selection)
        self.export_md_button.setEnabled(has_results)
        self.export_json_button.setEnabled(has_results)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ChatList")
        self.resize(980, 680)

        db.init_db()
        logger.info("Приложение ChatList запущено")

        self.tabs = QTabWidget()
        self.query_tab = QueryTab()
        self.models_tab = ModelsTab()
        self.prompts_tab = PromptsTab()
        self.history_tab = HistoryTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.query_tab, "Запрос")
        self.tabs.addTab(self.models_tab, "Модели")
        self.tabs.addTab(self.prompts_tab, "Промты")
        self.tabs.addTab(self.history_tab, "История")
        self.tabs.addTab(self.settings_tab, "Настройки")

        self.setCentralWidget(self.tabs)

        self.query_tab.load_saved_prompts()
        self._apply_theme()

        self.prompts_tab.use_prompt.connect(self._on_use_prompt)
        self.query_tab.saved.connect(self.history_tab.reload)
        self.query_tab.saved.connect(self.prompts_tab.reload)
        self.settings_tab.settings_saved.connect(self._apply_theme)

    def _on_use_prompt(self, prompt_id: int, prompt_text: str) -> None:
        self.query_tab.select_prompt(prompt_id, prompt_text)
        self.tabs.setCurrentWidget(self.query_tab)

    def _apply_theme(self) -> None:
        theme = db.get_setting("theme", "light") or "light"
        if theme.lower() == "dark":
            self.setStyleSheet(
                """
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                }
                QLineEdit, QPlainTextEdit, QComboBox, QTableWidget, QSpinBox, QTextBrowser {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #444;
                }
                QPushButton {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    padding: 6px 12px;
                }
                QPushButton:hover { background-color: #4a4a4a; }
                QHeaderView::section {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    border: 1px solid #444;
                }
                """
            )
        else:
            self.setStyleSheet("")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
