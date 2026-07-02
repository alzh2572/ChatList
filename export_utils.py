"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")


def export_to_markdown(items: list[dict[str, Any]], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# ChatList — экспорт результатов\n"]

    for index, item in enumerate(items, start=1):
        prompt = item.get("prompt", item.get("prompt_text", ""))
        model = item.get("model_name", item.get("model", ""))
        response = item.get("response", item.get("response_text", ""))
        created = item.get("created_at", "")

        lines.append(f"## {index}. {model}")
        if created:
            lines.append(f"**Дата:** {created}")
        if prompt:
            lines.append(f"\n**Промт:**\n\n{prompt}\n")
        lines.append(f"\n**Ответ:**\n\n{response}\n")
        lines.append("---\n")

    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def export_to_json(items: list[dict[str, Any]], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def default_export_path(extension: str) -> Path:
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    return exports_dir / f"chatlist_{_timestamp()}.{extension}"
