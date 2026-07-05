"""Тестовая программа для просмотра и редактирования SQLite-базы."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PAGE_SIZE = 50


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class RecordDialog(QDialog):
    def __init__(
        self,
        columns: list[dict[str, Any]],
        values: dict[str, Any] | None = None,
        *,
        is_edit: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.columns = columns
        self.is_edit = is_edit
        self.inputs: dict[str, QLineEdit] = {}

        self.setWindowTitle("Изменить запись" if is_edit else "Добавить запись")
        self.resize(480, 360)

        form = QFormLayout()
        for column in columns:
            name = str(column["name"])
            field = QLineEdit()
            if column["pk"] and column["type"].upper().startswith("INTEGER") and is_edit:
                field.setReadOnly(True)
            if values and name in values and values[name] is not None:
                field.setText(str(values[name]))
            self.inputs[name] = field
            form.addRow(f"{name}:", field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for column in self.columns:
            name = str(column["name"])
            text = self.inputs[name].text()
            if text == "":
                result[name] = None
            else:
                result[name] = text
        return result


class SQLiteBrowser(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SQLite Browser — test-db")
        self.resize(1100, 700)

        self.db_path: Path | None = None
        self.current_table: str | None = None
        self.columns: list[dict[str, Any]] = []
        self.primary_keys: list[str] = []
        self.current_page = 0
        self.total_rows = 0

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        file_row = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        open_file_btn = QPushButton("Выбрать SQLite...")
        open_file_btn.clicked.connect(self._choose_db_file)
        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(open_file_btn)
        layout.addLayout(file_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Таблицы:"))
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(self._open_selected_table)
        left_layout.addWidget(self.tables_list)

        open_table_btn = QPushButton("Открыть")
        open_table_btn.clicked.connect(self._open_selected_table)
        left_layout.addWidget(open_table_btn)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.table_title = QLabel("Выберите таблицу и нажмите «Открыть»")
        right_layout.addWidget(self.table_title)

        self.data_table = QTableWidget(0, 0)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.data_table)

        pagination_box = QGroupBox("Пагинация")
        pagination_row = QHBoxLayout(pagination_box)
        self.prev_btn = QPushButton("Назад")
        self.next_btn = QPushButton("Вперёд")
        self.page_label = QLabel("Страница 0 из 0")
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(10, 500)
        self.page_size_spin.setValue(PAGE_SIZE)
        self.page_size_spin.setSuffix(" строк")

        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        self.page_size_spin.valueChanged.connect(self._reload_current_table)

        pagination_row.addWidget(self.prev_btn)
        pagination_row.addWidget(self.next_btn)
        pagination_row.addWidget(self.page_label)
        pagination_row.addStretch()
        pagination_row.addWidget(QLabel("Размер страницы:"))
        pagination_row.addWidget(self.page_size_spin)
        right_layout.addWidget(pagination_box)

        crud_row = QHBoxLayout()
        self.add_btn = QPushButton("Добавить")
        self.edit_btn = QPushButton("Изменить")
        self.delete_btn = QPushButton("Удалить")
        self.refresh_btn = QPushButton("Обновить")

        self.add_btn.clicked.connect(self._add_record)
        self.edit_btn.clicked.connect(self._edit_record)
        self.delete_btn.clicked.connect(self._delete_record)
        self.refresh_btn.clicked.connect(self._reload_current_table)

        crud_row.addWidget(self.add_btn)
        crud_row.addWidget(self.edit_btn)
        crud_row.addWidget(self.delete_btn)
        crud_row.addWidget(self.refresh_btn)
        crud_row.addStretch()
        right_layout.addLayout(crud_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        self.setCentralWidget(central)
        self._set_table_actions_enabled(False)

    def _connect(self) -> sqlite3.Connection:
        if self.db_path is None:
            raise RuntimeError("База данных не выбрана")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _choose_db_file(self) -> None:
        default_path = str(Path.cwd() / "chatlist.db")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать SQLite",
            default_path,
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if not path:
            return
        self._load_database(Path(path))

    def _load_database(self, path: Path) -> None:
        try:
            conn = sqlite3.connect(path)
            tables = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
            conn.close()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу:\n{exc}")
            return

        self.db_path = path
        self.current_table = None
        self.current_page = 0
        self.total_rows = 0
        self.file_label.setText(str(path))
        self.tables_list.clear()
        for row in tables:
            self.tables_list.addItem(str(row[0]))

        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        self.table_title.setText("Выберите таблицу и нажмите «Открыть»")
        self.page_label.setText("Страница 0 из 0")
        self._set_table_actions_enabled(False)

    def _open_selected_table(self) -> None:
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "SQLite Browser", "Выберите таблицу из списка.")
            return
        self.current_table = item.text()
        self.current_page = 0
        self._load_table_metadata()
        self._reload_current_table()

    def _load_table_metadata(self) -> None:
        if not self.current_table:
            return
        conn = self._connect()
        try:
            rows = conn.execute(f'PRAGMA table_info("{self.current_table}")').fetchall()
            self.columns = [row_to_dict(row) for row in rows]
            self.primary_keys = [
                str(column["name"]) for column in self.columns if column["pk"]
            ]
        finally:
            conn.close()

    def _reload_current_table(self) -> None:
        if not self.current_table:
            return

        page_size = self.page_size_spin.value()
        offset = self.current_page * page_size

        conn = self._connect()
        try:
            self.total_rows = conn.execute(
                f'SELECT COUNT(*) FROM "{self.current_table}"'
            ).fetchone()[0]
            rows = conn.execute(
                f'SELECT * FROM "{self.current_table}" LIMIT ? OFFSET ?',
                (page_size, offset),
            ).fetchall()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить таблицу:\n{exc}")
            return
        finally:
            conn.close()

        column_names = [str(column["name"]) for column in self.columns]
        self.data_table.setSortingEnabled(False)
        self.data_table.setColumnCount(len(column_names))
        self.data_table.setHorizontalHeaderLabels(column_names)
        self.data_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            record = row_to_dict(row)
            for col_index, name in enumerate(column_names):
                value = record.get(name)
                text = "" if value is None else str(value)
                self.data_table.setItem(row_index, col_index, QTableWidgetItem(text))

        total_pages = max(1, (self.total_rows + page_size - 1) // page_size)
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        self.table_title.setText(
            f"Таблица: {self.current_table} ({self.total_rows} записей)"
        )
        self.page_label.setText(
            f"Страница {self.current_page + 1} из {total_pages}"
        )
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled((self.current_page + 1) * page_size < self.total_rows)
        self._set_table_actions_enabled(True)

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._reload_current_table()

    def _next_page(self) -> None:
        page_size = self.page_size_spin.value()
        if (self.current_page + 1) * page_size < self.total_rows:
            self.current_page += 1
            self._reload_current_table()

    def _selected_record(self) -> dict[str, Any] | None:
        row = self.data_table.currentRow()
        if row < 0 or not self.columns:
            return None

        record: dict[str, Any] = {}
        for col_index, column in enumerate(self.columns):
            name = str(column["name"])
            item = self.data_table.item(row, col_index)
            record[name] = None if item is None else item.text()
        return record

    def _insertable_columns(self) -> list[dict[str, Any]]:
        return [
            column
            for column in self.columns
            if not (column["pk"] and column["type"].upper().startswith("INTEGER"))
        ]

    def _add_record(self) -> None:
        if not self.current_table:
            return

        dialog = RecordDialog(self._insertable_columns(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values_dict()
        columns = list(values.keys())
        placeholders = ", ".join("?" for _ in columns)
        names = ", ".join(f'"{name}"' for name in columns)
        sql = f'INSERT INTO "{self.current_table}" ({names}) VALUES ({placeholders})'

        conn = self._connect()
        try:
            conn.execute(sql, [values[name] for name in columns])
            conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись:\n{exc}")
            return
        finally:
            conn.close()

        self._reload_current_table()

    def _edit_record(self) -> None:
        if not self.current_table:
            return

        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "SQLite Browser", "Выберите запись для изменения.")
            return

        dialog = RecordDialog(self.columns, record, is_edit=True, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        values = dialog.values_dict()
        if not self.primary_keys:
            QMessageBox.warning(
                self,
                "SQLite Browser",
                "У таблицы нет первичного ключа — изменение невозможно.",
            )
            return

        set_parts = []
        set_values = []
        for column in self.columns:
            name = str(column["name"])
            if name in self.primary_keys:
                continue
            set_parts.append(f'"{name}" = ?')
            set_values.append(values[name])

        where_parts = [f'"{name}" = ?' for name in self.primary_keys]
        where_values = [record[name] for name in self.primary_keys]
        sql = (
            f'UPDATE "{self.current_table}" SET {", ".join(set_parts)} '
            f'WHERE {" AND ".join(where_parts)}'
        )

        conn = self._connect()
        try:
            conn.execute(sql, set_values + where_values)
            conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось изменить запись:\n{exc}")
            return
        finally:
            conn.close()

        self._reload_current_table()

    def _delete_record(self) -> None:
        if not self.current_table:
            return

        record = self._selected_record()
        if record is None:
            QMessageBox.information(self, "SQLite Browser", "Выберите запись для удаления.")
            return

        answer = QMessageBox.question(
            self,
            "SQLite Browser",
            "Удалить выбранную запись?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if not self.primary_keys:
            QMessageBox.warning(
                self,
                "SQLite Browser",
                "У таблицы нет первичного ключа — удаление невозможно.",
            )
            return

        where_parts = [f'"{name}" = ?' for name in self.primary_keys]
        where_values = [record[name] for name in self.primary_keys]
        sql = f'DELETE FROM "{self.current_table}" WHERE {" AND ".join(where_parts)}'

        conn = self._connect()
        try:
            conn.execute(sql, where_values)
            conn.commit()
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "SQLite Browser", f"Не удалось удалить запись:\n{exc}")
            return
        finally:
            conn.close()

        self._reload_current_table()

    def _set_table_actions_enabled(self, enabled: bool) -> None:
        for widget in (
            self.prev_btn,
            self.next_btn,
            self.page_size_spin,
            self.add_btn,
            self.edit_btn,
            self.delete_btn,
            self.refresh_btn,
        ):
            widget.setEnabled(enabled)


def main() -> None:
    app = QApplication(sys.argv)
    window = SQLiteBrowser()

    default_db = Path("chatlist.db")
    if default_db.exists():
        window._load_database(default_db)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
