# Публикация ChatList на GitHub

Пошаговая инструкция: **GitHub Release** (Windows-дистрибутивы) и **GitHub Pages** (HTML-лендинг).

---

## Быстрый старт

| Цель | Команды |
|------|---------|
| **Первый раз** | `git push origin main` → включить Pages → проверить Actions |
| **Новый Release** | обновить `version.py` → `.\scripts\prepare-release.ps1` → `git tag vX.Y.Z` → `git push origin main --tags` |
| **Обновить лендинг** | правки в `docs/` → `git push origin main` |

**Ссылки проекта:**
- Репозиторий: https://github.com/alzh2572/ChatList
- Лендинг: https://alzh2572.github.io/ChatList/
- Releases: https://github.com/alzh2572/ChatList/releases

---

## Файлы и шаблоны

```
docs/
  index.html                    # HTML-лендинг
  config.js                     # owner/repo для ссылок и GitHub API

.github/
  RELEASE_NOTES.template.md     # шаблон описания Release ({{VERSION}})
  workflows/
    pages.yml                   # деплой лендинга на GitHub Pages
    release.yml                 # сборка exe + Release по тегу v*

scripts/
  prepare-release.ps1           # локальная сборка, checksums, release notes

PUBLISHING.md                   # эта инструкция
build.ps1                       # PyInstaller + Inno Setup
version.py                      # единственный источник версии (__version__)
```

---

## Часть 1. Первоначальная настройка (один раз)

### Шаг 1. Отправьте код на GitHub

```powershell
cd c:\Work\ChatList
git remote -v
git push origin main
```

Remote уже настроен: `https://github.com/alzh2572/ChatList.git`

### Шаг 2. Лендинг — репозиторий в config.js

В `docs/config.js`:

```javascript
window.CHATLIST_REPO = "alzh2572/ChatList";
```

Лендинг (`docs/index.html`) автоматически подтягивает последний Release через GitHub API и показывает кнопки «Скачать».

**Локальный предпросмотр:**

```powershell
cd c:\Work\ChatList\docs
python -m http.server 8080
```

Откройте http://localhost:8080

### Шаг 3. Включите GitHub Pages

Pages уже включены (`build_type: workflow`). Если нужно включить заново:

**Веб:** [Settings → Pages](https://github.com/alzh2572/ChatList/settings/pages) → **Source** → **GitHub Actions**

**CLI:**

```powershell
gh api --method POST repos/alzh2572/ChatList/pages -f build_type=workflow
```

### Шаг 4. Проверьте workflows

После `git push origin main` в [Actions](https://github.com/alzh2572/ChatList/actions) должны появиться:

| Workflow | Файл | Когда запускается |
|----------|------|-------------------|
| Deploy GitHub Pages | `pages.yml` | push в `docs/` или вручную |
| Release | `release.yml` | push тега `v*` |

```powershell
Get-ChildItem .github\workflows
gh workflow list -R alzh2572/ChatList
gh workflow run "Deploy GitHub Pages" --ref main
```

> **Важно:** если workflows не видны на GitHub — выполните `git push origin main` (локальная ветка может быть впереди origin).

---

## Часть 2. Публикация Release (новая версия)

### Шаг 1. Обновите версию

Единственный источник — `version.py`:

```python
__version__ = "1.0.0"
```

### Шаг 2. Заполните «Что нового»

Отредактируйте блок в `.github/RELEASE_NOTES.template.md`:

```markdown
### Что нового

- описание изменений
```

### Шаг 3. Соберите артефакты локально

```powershell
cd c:\Work\ChatList
.\scripts\prepare-release.ps1
```

Скрипт создаёт:
- `dist/ChatList-<версия>.exe` — portable
- `dist/ChatList-<версия>-setup.exe` — установщик Inno Setup
- `dist/checksums.txt` — SHA256
- `dist/RELEASE_NOTES.md` — текст для Release

Проверьте и допишите `dist/RELEASE_NOTES.md`.  
Если сборка уже выполнена: `.\scripts\prepare-release.ps1 -SkipBuild`

### Шаг 4. Коммит, тег и push

```powershell
git add version.py .github/RELEASE_NOTES.template.md
git commit -m "Release v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

Тег **обязательно** с префиксом `v` (`v1.0.0`, не `1.0.0`).

### Шаг 5. Дождитесь GitHub Actions

1. [Actions → Release](https://github.com/alzh2572/ChatList/actions/workflows/release.yml)
2. В [Releases](https://github.com/alzh2572/ChatList/releases) появятся:
   - `ChatList-1.0.0-setup.exe`
   - `ChatList-1.0.0.exe`
   - `checksums.txt`

```powershell
gh release view v1.0.0
```

### Шаг 6. Проверьте лендинг

После Release кнопки на https://alzh2572.github.io/ChatList/ начнут вести на актуальные файлы.

---

## Часть 3. Публикация лендинга (GitHub Pages)

### Автоматически

При push в `main` с изменениями в `docs/`:

```powershell
git add docs/
git commit -m "Обновить лендинг"
git push origin main
```

### Вручную

[Actions → Deploy GitHub Pages → Run workflow](https://github.com/alzh2572/ChatList/actions/workflows/pages.yml)

```powershell
gh workflow run "Deploy GitHub Pages" --ref main
gh run list --workflow=pages.yml
```

---

## Release вручную (без Actions)

```powershell
.\scripts\prepare-release.ps1
# отредактируйте dist/RELEASE_NOTES.md
gh release create v1.0.0 `
  "dist/ChatList-1.0.0-setup.exe" `
  "dist/ChatList-1.0.0.exe" `
  "dist/checksums.txt" `
  --title "ChatList 1.0.0" `
  --notes-file dist/RELEASE_NOTES.md
```

---

## Чек-лист перед релизом

- [ ] `version.py` обновлён
- [ ] `.github/RELEASE_NOTES.template.md` — заполнен блок «Что нового»
- [ ] `docs/config.js` — `alzh2572/ChatList`
- [ ] `.\build.ps1` проходит без ошибок
- [ ] Тег `vX.Y.Z` создан и отправлен
- [ ] Workflow **Release** завершился успешно
- [ ] Лендинг показывает версию и кнопки скачивания
- [ ] Установщик и portable работают на Windows

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Workflows не видны | `git push origin main` |
| Pages не открывается | Settings → Pages → Source = **GitHub Actions** |
| Кнопки «Скачать» неактивны | Опубликуйте Release; проверьте `docs/config.js` |
| Release workflow не запустился | Тег должен быть `v1.0.0`, не `1.0.0` |
| Inno Setup не найден в CI | Workflow ставит через `choco install innosetup` |

---

## Полезные ссылки

- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub Pages](https://docs.github.com/en/pages)
- [GitHub Actions](https://docs.github.com/en/actions)
