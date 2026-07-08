"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx

import db
from log_utils import get_logger
from models import AIModel, load_api_key

logger = get_logger()


@dataclass
class ModelResponse:
    model_id: int
    model_name: str
    response_text: str
    error: str | None = None


def _extract_openai_compatible_content(data: dict) -> str:
    choices = data.get("choices")
    if not choices:
        raise ValueError("API не вернул choices в ответе")
    message = choices[0].get("message", {})
    content = message.get("content")
    if content is None:
        raise ValueError("API не вернул content в ответе")
    return str(content)


def send_prompt_to_model(
    prompt: str,
    model: AIModel,
    timeout: float | None = None,
    system_message: str | None = None,
) -> ModelResponse:
    if timeout is None:
        timeout = float(db.get_setting("request_timeout", "60") or "60")

    api_key = load_api_key(model.api_id)
    if api_key is None:
        return ModelResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"API-ключ не найден: переменная {model.api_id} в .env",
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter.ai" in model.api_url:
        headers["HTTP-Referer"] = "https://github.com/ChatList"
        headers["X-Title"] = "ChatList"

    payload = {
        "model": model.name,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_message:
        payload["messages"] = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

    try:
        logger.info("Запрос к модели %s (%s)", model.name, model.api_url)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(model.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        text = _extract_openai_compatible_content(data)
        logger.info("Успешный ответ от модели %s (%d символов)", model.name, len(text))
        return ModelResponse(
            model_id=model.id,
            model_name=model.name,
            response_text=text,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        logger.error("HTTP-ошибка модели %s: %s", model.name, detail)
        return ModelResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"HTTP {exc.response.status_code}: {detail}",
        )
    except httpx.RequestError as exc:
        logger.error("Сетевая ошибка модели %s: %s", model.name, exc)
        return ModelResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"Ошибка сети: {exc}",
        )
    except (ValueError, KeyError, IndexError) as exc:
        logger.error("Ошибка разбора ответа модели %s: %s", model.name, exc)
        return ModelResponse(
            model_id=model.id,
            model_name=model.name,
            response_text="",
            error=f"Ошибка разбора ответа: {exc}",
        )


def send_prompt_to_all_models(
    prompt: str,
    models: list[AIModel],
    timeout: float | None = None,
) -> list[ModelResponse]:
    if not models:
        return []

    results: list[ModelResponse] = []
    with ThreadPoolExecutor(max_workers=min(len(models), 8)) as executor:
        futures = {
            executor.submit(send_prompt_to_model, prompt, model, timeout): model
            for model in models
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item.model_name.lower())
    return results
