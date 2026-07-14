## ChatList {{VERSION}}

### Скачать (Windows)

| Файл | Описание |
|------|----------|
| `ChatList-{{VERSION}}-setup.exe` | Установщик (рекомендуется) |
| `ChatList-{{VERSION}}.exe` | Portable-версия без установки |
| `checksums.txt` | SHA256 контрольные суммы |

### Установка

1. Скачайте `ChatList-{{VERSION}}-setup.exe`.
2. Запустите установщик и следуйте инструкциям.
3. Создайте файл `.env` в каталоге программы (или скопируйте из `.env.example` в репозитории):

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

4. Запустите ChatList из меню «Пуск».

### Portable

1. Скачайте `ChatList-{{VERSION}}.exe`.
2. Положите `.env` с API-ключом в ту же папку.
3. Запустите exe-файл.

### Проверка целостности (PowerShell)

```powershell
Get-FileHash .\ChatList-{{VERSION}}-setup.exe -Algorithm SHA256
```

Сравните результат со значением в `checksums.txt`.

### Что нового

- 

### Системные требования

- Windows 10/11 (64-bit)
- API-ключ OpenRouter
