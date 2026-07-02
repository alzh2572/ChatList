"""Вспомогательные функции для таблиц GUI."""

from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit, QTableWidget


def setup_sortable_table(table: QTableWidget) -> None:
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)


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
