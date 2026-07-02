"""Логика работы с моделями нейросетей."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

import db

load_dotenv()


@dataclass
class AIModel:
    id: int
    name: str
    api_url: str
    api_id: str
    is_active: bool

    @classmethod
    def from_row(cls, row: dict) -> AIModel:
        return cls(
            id=int(row["id"]),
            name=str(row["name"]),
            api_url=str(row["api_url"]),
            api_id=str(row["api_id"]),
            is_active=bool(row["is_active"]),
        )


def load_api_key(api_id: str) -> str | None:
    value = os.getenv(api_id)
    if value is None or not value.strip():
        return None
    return value.strip()


def get_active_models() -> list[AIModel]:
    rows = db.list_active_models()
    return [AIModel.from_row(row) for row in rows]


def get_all_models() -> list[AIModel]:
    rows = db.list_models()
    return [AIModel.from_row(row) for row in rows]


def get_model_by_id(model_id: int) -> AIModel | None:
    row = db.get_model(model_id)
    if row is None:
        return None
    return AIModel.from_row(row)
