# Публикация ChatList на GitHub

Пошаговая инструкция: GitHub Release (дистрибутивы) и GitHub Pages (лендинг).

---

## Подготовка (один раз)

### 1. Создайте репозиторий на GitHub

```powershell
cd c:\Work\ChatList
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/ChatList.git
git push -u origin main
```

### 2. Укажите репозиторий в лендинге

Откройте `docs/config.js` и замените placeholder:

```javascript
window.CHATLIST_REPO = "YOUR_GITHUB_USERNAME/ChatList";
```

### 3. Включите GitHub Pages

1. Откройте репозиторий на GitHub → **Settings** → **Pages**
2. В **Build and deployment** → **Source** выберите **GitHub Actions**
3. После первого push в `docs/` или ручного запуска workflow **Deploy GitHub Pages** сайт будет доступен по адресу:

```
https://YOUR_GITHUB_USERNAME.github.io/ChatList/
```

### 4. Проверьте workflows

В репозитории должны появиться два workflow:

| Файл | Назначение |
|------|------------|
| `.github/workflows/pages.yml` | Публикация лендинга из папки `docs/` |
| `.github/workflows/release.yml` | Сборка Windows и создание Release по тегу `v*` |

---

## Публикация новой версии (GitHub Release)

### Шаг 1. Обновите версию

Единственный источник версии — `version.py`:

```python
__version__ = "1.0.0"
```

### Шаг 2. Заполните список изменений

Отредактируйте блок «Что нового» в `.github/RELEASE_NOTES.template.md` (или позже — в сгенерированном `dist/RELEASE_NOTES.md`).

### Шаг 3. Соберите артефакты локально (рекомендуется)

```powershell
cd c:\Work\ChatList
.\scripts\prepare-release.ps1
```

Скрипт:
- запускает `build.ps1` (exe + установщик Inno Setup);
- создаёт `dist/checksums.txt` (SHA256);
- создаёт `dist/RELEASE_NOTES.md` из шаблона.

Проверьте и допишите «Что нового» в `dist/RELEASE_NOTES.md`.

> Если сборка уже выполнена: `.\scripts\prepare-release.ps1 -SkipBuild`

### Шаг 4. Закоммитьте и создайте тег

```powershell
git add version.py .github/RELEASE_NOTES.template.md
git commit -m "Release v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

**Важно:** тег должен начинаться с `v` (например `v1.0.0`) — так настроен workflow `release.yml`.

### Шаг 5. Дождитесь GitHub Actions

1. Откройте **Actions** → workflow **Release**
2. После успешной сборки в **Releases** появятся файлы:
   - `ChatList-1.0.0-setup.exe` — установщик
   - `ChatList-1.0.0.exe` — portable
   - `checksums.txt` — контрольные суммы

### Шаг 6. Проверьте Release

```powershell
gh release view v1.0.0
```

Или откройте: `https://github.com/YOUR_GITHUB_USERNAME/ChatList/releases`

---

## Публикация вручную (без Actions)

Если workflow недоступен:

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

## Публикация лендинга (GitHub Pages)

### Автоматически

При push в `main` с изменениями в `docs/` запускается workflow **Deploy GitHub Pages**.

```powershell
git add docs/
git commit -m "Обновить лендинг"
git push origin main
```

### Вручную

1. **Actions** → **Deploy GitHub Pages** → **Run workflow**

### Локальный предпросмотр

```powershell
cd c:\Work\ChatList\docs
python -m http.server 8080
```

Откройте `http://localhost:8080` (кнопки скачивания заработают после публикации Release и настройки `config.js`).

---

## Структура файлов публикации

```
docs/
  index.html          # HTML-лендинг
  config.js           # имя репозитория для ссылок и API

.github/
  RELEASE_NOTES.template.md   # шаблон описания Release
  workflows/
    pages.yml         # деплой GitHub Pages
    release.yml       # сборка и Release по тегу

scripts/
  prepare-release.ps1 # локальная подготовка Release
```

---

## Чек-лист перед релизом

- [ ] `version.py` обновлён
- [ ] `.github/RELEASE_NOTES.template.md` — заполнен блок «Что нового»
- [ ] `docs/config.js` — указан правильный `username/ChatList`
- [ ] Локальная сборка `.\build.ps1` проходит без ошибок
- [ ] Тег `vX.Y.Z` создан и отправлен на GitHub
- [ ] Workflow **Release** завершился успешно
- [ ] На лендинге отображается версия и работают кнопки скачивания
- [ ] Установщик и portable запускаются на чистой Windows

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Pages не открывается | Settings → Pages → Source = **GitHub Actions** |
| Кнопки «Скачать» неактивны | Опубликуйте Release; проверьте `docs/config.js` |
| Release workflow не запустился | Тег должен быть `v1.0.0`, не `1.0.0` |
| Inno Setup не найден в CI | Workflow ставит через `choco install innosetup` |
| Дублирование exe в Release | Используйте `prepare-release.ps1` / актуальный `release.yml` |

---

## Полезные ссылки

- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [GitHub Pages](https://docs.github.com/en/pages)
- [GitHub Actions](https://docs.github.com/en/actions)
