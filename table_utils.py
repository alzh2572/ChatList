"""Вспомогательные функции для таблиц GUI."""

from __future__ import annotations

from PyQt6.QtWidgets import QHeaderView, QLineEdit, QTableWidget


def setup_sortable_table(table: QTableWidget) -> None:
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)


def setup_multiline_table(table: QTableWidget, min_row_height: int = 96) -> None:
    table.setWordWrap(True)
    table.verticalHeader().setMinimumSectionSize(min_row_height)
    table.verticalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )


def resize_table_rows(table: QTableWidget, min_row_height: int = 96) -> None:
    table.resizeRowsToContents()
    for row_index in range(table.rowCount()):
        if table.rowHeight(row_index) < min_row_height:
            table.setRowHeight(row_index, min_row_height)


def connect_search(table: QTableWidget, search_input: QLineEdit, columns: list[int]) -> None:
    def apply_filter() -> None:
        query = search_input.text().strip().lower()
        for row in range(table.rowCount()):
            if not query:
                table.setRowHidden(row, False)
                continue
            visible = False
            for col in columns:
                item = table.item(row, col)
                if item and query in item.text().lower():
                    visible = True
                    break
            table.setRowHidden(row, not visible)

    search_input.textChanged.connect(apply_filter)
