"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from models import AIModel
from network import send_prompt_to_model

SYSTEM_PROMPT = """Ты — ассистент по улучшению промтов для нейросетей.
Пользователь пришлёт исходный промт. Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{
  "improved": "улучшенная версия промта",
  "alternatives": ["вариант 1", "вариант 2", "вариант 3"],
  "adaptations": {
    "code": "адаптация для задач по коду",
    "analysis": "адаптация для анализа",
    "creative": "адаптация для креатива"
  }
}
alternatives — ровно 2–3 переформулировки. adaptations — опционально, заполняй если уместно."""


@dataclass
class PromptImprovementResult:
    original: str
    improved: str = ""
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def improve_prompt(text: str, model: AIModel) -> PromptImprovementResult:
    original = text.strip()
    if not original:
        return PromptImprovementResult(original=original, error="Промт пустой")

    user_message = f"Исходный промт:\n\n{original}"
    response = send_prompt_to_model(
        user_message,
        model,
        system_message=SYSTEM_PROMPT,
    )

    if response.error:
        return PromptImprovementResult(original=original, error=response.error)

    try:
        data = _extract_json(response.response_text)
        improved = str(data.get("improved", "")).strip()
        alternatives = [
            str(item).strip()
            for item in data.get("alternatives", [])
            if str(item).strip()
        ]
        adaptations_raw = data.get("adaptations") or {}
        adaptations = {
            str(key): str(value).strip()
            for key, value in adaptations_raw.items()
            if str(value).strip()
        }

        if not improved:
            improved = response.response_text.strip()

        return PromptImprovementResult(
            original=original,
            improved=improved,
            alternatives=alternatives[:3],
            adaptations=adaptations,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return PromptImprovementResult(
            original=original,
            improved=response.response_text.strip(),
            error=f"Ответ модели не в формате JSON, показан как есть ({exc})",
        )
