import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import db
from models import get_active_models
from network import ModelResponse, send_prompt_to_all_models
from session import QuerySession


class RequestWorker(QThread):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self.prompt = prompt

    def run(self) -> None:
        try:
            models = get_active_models()
            responses = send_prompt_to_all_models(self.prompt, models)
            self.finished.emit(responses)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.session = QuerySession()
        self.worker: RequestWorker | None = None

        self.setWindowTitle("ChatList")
        self.resize(900, 600)

        db.init_db()

        central = QWidget()
        layout = QVBoxLayout(central)

        layout.addWidget(self._build_prompt_section())
        layout.addWidget(self._build_results_section())
        layout.addWidget(self._build_actions_section())

        self.setCentralWidget(central)
        self._load_saved_prompts()

    def _build_prompt_section(self) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)

        saved_label = QLabel("Сохранённые промты:")
        self.prompt_combo = QComboBox()
        self.prompt_combo.setPlaceholderText("Выберите сохранённый промт")
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)

        input_label = QLabel("Промт:")
        self.prompt_input = QPlainTextEdit()
        self.prompt_input.setPlaceholderText("Введите текст запроса...")
        self.prompt_input.setMaximumHeight(120)

        send_row = QHBoxLayout()
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self._on_send)
        send_row.addStretch()
        send_row.addWidget(self.send_button)

        section_layout.addWidget(saved_label)
        section_layout.addWidget(self.prompt_combo)
        section_layout.addWidget(input_label)
        section_layout.addWidget(self.prompt_input)
        section_layout.addLayout(send_row)

        return section

    def _build_results_section(self) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)

        section_layout.addWidget(QLabel("Результаты:"))

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Модель", "Ответ", "Выбрать"])
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        section_layout.addWidget(self.progress)
        section_layout.addWidget(self.results_table)

        return section

    def _build_actions_section(self) -> QWidget:
        section = QWidget()
        row = QHBoxLayout(section)

        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self._on_save)
        self.save_button.setEnabled(False)

        self.new_button = QPushButton("Новый запрос")
        self.new_button.clicked.connect(self._on_new_query)

        row.addWidget(self.save_button)
        row.addWidget(self.new_button)
        row.addStretch()

        return section

    def _load_saved_prompts(self) -> None:
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

    def _on_prompt_selected(self, index: int) -> None:
        prompt_id = self.prompt_combo.itemData(index)
        if prompt_id is None:
            return
        record = db.get_prompt(int(prompt_id))
        if record:
            self.prompt_input.setPlainText(record["prompt"])

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
                "Нет активных моделей. Добавьте модели в базу данных.",
            )
            return

        combo_index = self.prompt_combo.currentIndex()
        prompt_id = self.prompt_combo.itemData(combo_index)
        if prompt_id is None:
            prompt_id = db.create_prompt(prompt_text)
            self._load_saved_prompts()
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
        self.results_table.setRowCount(len(self.session.rows))

        for row_index, row in enumerate(self.session.rows):
            model_item = QTableWidgetItem(row.model_name)
            response_item = QTableWidgetItem(row.response)
            if row.error:
                response_item.setForeground(Qt.GlobalColor.red)

            select_item = QTableWidgetItem()
            select_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            select_item.setCheckState(
                Qt.CheckState.Checked if row.selected else Qt.CheckState.Unchecked
            )

            self.results_table.setItem(row_index, 0, model_item)
            self.results_table.setItem(row_index, 1, response_item)
            self.results_table.setItem(row_index, 2, select_item)

        self.results_table.itemChanged.connect(self._on_result_item_changed)
        self.save_button.setEnabled(self.session.has_results())

    def _on_result_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 2:
            return
        self.session.set_selected(item.row(), item.checkState() == Qt.CheckState.Checked)

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
        self.session.clear()
        self._clear_results_table()

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
        try:
            self.results_table.itemChanged.disconnect(self._on_result_item_changed)
        except TypeError:
            pass
        self.results_table.setRowCount(0)
        self.save_button.setEnabled(False)

    def _set_loading(self, loading: bool) -> None:
        self.progress.setVisible(loading)
        self.send_button.setEnabled(not loading)
        self.save_button.setEnabled(not loading and self.session.has_results())
        self.new_button.setEnabled(not loading)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
