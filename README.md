# ChatList

Приложение для отправки одного промта в несколько нейросетей и сравнения ответов.

## Возможности

- Отправка промта во все активные модели параллельно
- Временная таблица результатов с выбором строк для сохранения
- Управление моделями, промтами и историей результатов
- Экспорт в Markdown и JSON
- Настройки таймаута и темы интерфейса
- Логирование запросов в `logs/chatlist.log`

## Требования

- Python 3.11+
- Windows / Linux / macOS

## Установка

```powershell
cd c:\Work\ChatList
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Откройте `.env` и укажите API-ключ OpenRouter:

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

## Запуск

```powershell
python main.py
```

При первом запуске создаётся база `chatlist.db` с двумя бесплатными моделями OpenRouter:

- `poolside/laguna-xs-2.1:free`
- `cohere/north-mini-code:free`

Модели можно просматривать на вкладке **Модели**.

## Структура проекта

| Файл | Назначение |
|------|------------|
| `main.py` | GUI и точка входа |
| `db.py` | Работа с SQLite |
| `models.py` | Логика моделей нейросетей |
| `network.py` | HTTP-запросы к API |
| `session.py` | Временная таблица результатов |
| `gui_tabs.py` | Вкладки управления |
| `export_utils.py` | Экспорт MD/JSON |
| `log_utils.py` | Логирование |

## Сборка exe и установщика

Версия приложения задаётся в `version.py` (`__version__`).

```powershell
pip install pyinstaller
.\build.ps1
```

Результат:
- `dist\ChatList-<версия>.exe` — исполняемый файл
- `dist\ChatList-<версия>-setup.exe` — установщик (если установлен Inno Setup)

## Документация

- [PROJECT.md](PROJECT.md) — спецификация
- [PLAN.md](PLAN.md) — план реализации
- [DATABASE.md](DATABASE.md) — схема базы данных
