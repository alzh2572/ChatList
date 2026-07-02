# Схема базы данных ChatList

База данных: **SQLite** (файл, например `chatlist.db`).

Доступ к БД инкапсулирован в модуле `db.py`. API-ключи **не хранятся** в базе — только имя переменной окружения.

---

## ER-диаграмма (логическая)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   prompts   │       │   results   │       │   models    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ prompt_id   │       │ id (PK)     │
│ created_at  │       │ model_id    │──────►│ name        │
│ prompt      │       │ response    │       │ api_url     │
│ tags        │       │ created_at  │       │ api_id      │
└─────────────┘       └─────────────┘       │ is_active   │
                                            └─────────────┘

┌─────────────┐
│  settings   │
├─────────────┤
│ key (PK)    │
│ value       │
└─────────────┘
```

---

## Таблица `prompts`

Хранит сохранённые промты пользователя.

| Поле        | Тип          | Ограничения        | Описание                              |
|-------------|--------------|--------------------|---------------------------------------|
| `id`        | INTEGER      | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор       |
| `created_at`| TEXT         | NOT NULL           | Дата и время создания (ISO 8601)      |
| `prompt`    | TEXT         | NOT NULL           | Текст промта                          |
| `tags`      | TEXT         | NULL               | Теги через запятую, например `code,sql` |

**Индексы:**
- `idx_prompts_created_at` — сортировка по дате
- `idx_prompts_tags` — опционально, для поиска по тегам

---

## Таблица `models`

Список нейросетей, доступных для отправки запросов.

| Поле        | Тип          | Ограничения        | Описание                                      |
|-------------|--------------|--------------------|-----------------------------------------------|
| `id`        | INTEGER      | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор               |
| `name`      | TEXT         | NOT NULL UNIQUE    | Отображаемое имя модели, например `GPT-4o`    |
| `api_url`   | TEXT         | NOT NULL           | URL endpoint API                              |
| `api_id`    | TEXT         | NOT NULL           | Имя переменной в `.env`, например `OPENAI_API_KEY` |
| `is_active` | INTEGER      | NOT NULL DEFAULT 1 | `1` — активна, `0` — отключена                |

> **Важно:** в поле `api_id` хранится только имя переменной окружения. Значение ключа читается из файла `.env` при выполнении запроса.

**Индексы:**
- `idx_models_is_active` — быстрый выбор активных моделей

---

## Таблица `results`

Постоянное хранение ответов, отмеченных пользователем для сохранения.

| Поле        | Тип          | Ограничения        | Описание                              |
|-------------|--------------|--------------------|---------------------------------------|
| `id`        | INTEGER      | PRIMARY KEY AUTOINCREMENT | Уникальный идентификатор       |
| `prompt_id` | INTEGER      | NOT NULL, FK → `prompts.id` | Связь с промтом              |
| `model_id`  | INTEGER      | NOT NULL, FK → `models.id`  | Связь с моделью              |
| `response`  | TEXT         | NOT NULL           | Текст ответа нейросети                |
| `created_at`| TEXT         | NOT NULL           | Дата и время сохранения (ISO 8601)    |

**Внешние ключи:**
- `prompt_id` → `prompts(id)` ON DELETE CASCADE
- `model_id` → `models(id)` ON DELETE RESTRICT

**Индексы:**
- `idx_results_prompt_id`
- `idx_results_model_id`
- `idx_results_created_at`

---

## Таблица `settings`

Key-value хранилище настроек программы.

| Поле   | Тип  | Ограничения | Описание                    |
|--------|------|-------------|-----------------------------|
| `key`  | TEXT | PRIMARY KEY | Ключ настройки              |
| `value`| TEXT | NOT NULL    | Значение настройки (строка) |

**Примеры записей:**

| key              | value              | Описание                          |
|------------------|--------------------|-----------------------------------|
| `db_path`        | `chatlist.db`      | Путь к файлу базы данных          |
| `request_timeout`| `60`               | Таймаут HTTP-запроса (секунды)    |
| `theme`          | `light`            | Тема интерфейса                   |

---

## Временная таблица результатов (не в SQLite)

При отправке промта программа создаёт **временную структуру в памяти** (не сохраняется в БД):

| Поле          | Тип     | Описание                              |
|---------------|---------|---------------------------------------|
| `model_name`  | TEXT    | Название модели                       |
| `model_id`    | INTEGER | ID модели (для сохранения в `results`)|
| `response`    | TEXT    | Текст ответа или сообщение об ошибке  |
| `selected`    | BOOL    | Отмечен ли пользователем для сохранения |

**Жизненный цикл:**
1. Создаётся после отправки промта во все активные модели.
2. Очищается при нажатии «Сохранить» (после записи выбранных строк в `results`).
3. Полностью удаляется и пересоздаётся при вводе нового промта.

---

## SQL: создание таблиц

```sql
CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    prompt     TEXT    NOT NULL,
    tags       TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    api_url    TEXT    NOT NULL,
    api_id     TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL,
    model_id   INTEGER NOT NULL,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active  ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id  ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
```

---

## Примечания по данным

1. **Промт перед отправкой:** если пользователь вводит новый промт, его можно сохранить в `prompts` при первой отправке или только при сохранении результатов — решение зафиксировать в `db.py` при реализации.
2. **API-ключи:** файл `.env` в корне проекта, формат `ИМЯ_ПЕРЕМЕННОЙ=значение`. Пример: `OPENAI_API_KEY=sk-...`.
3. **Даты:** хранить в формате ISO 8601 (`2026-07-03T13:29:00`) для единообразной сортировки и отображения.
