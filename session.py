"""Временная таблица результатов текущего запроса (в памяти)."""

from __future__ import annotations

from dataclasses import dataclass, field

from network import ModelResponse


@dataclass
class ResultRow:
    model_id: int
    model_name: str
    response: str
    selected: bool = False
    error: str | None = None


@dataclass
class QuerySession:
    prompt_text: str = ""
    prompt_id: int | None = None
    rows: list[ResultRow] = field(default_factory=list)

    def clear(self) -> None:
        self.prompt_text = ""
        self.prompt_id = None
        self.rows.clear()

    def start_new_prompt(self, prompt_text: str, prompt_id: int | None = None) -> None:
        self.prompt_text = prompt_text
        self.prompt_id = prompt_id
        self.rows.clear()

    def set_results(self, responses: list[ModelResponse]) -> None:
        self.rows = [
            ResultRow(
                model_id=item.model_id,
                model_name=item.model_name,
                response=item.response_text if not item.error else f"[Ошибка] {item.error}",
                selected=False,
                error=item.error,
            )
            for item in responses
        ]

    def set_selected(self, index: int, selected: bool) -> None:
        if 0 <= index < len(self.rows):
            self.rows[index].selected = selected

    def get_selected_rows(self) -> list[ResultRow]:
        return [row for row in self.rows if row.selected]

    def has_results(self) -> bool:
        return bool(self.rows)
