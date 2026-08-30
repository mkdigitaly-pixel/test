# Автопубликация mkekspert

Цепочка: **агент пишет → вы согласовываете → скрипт публикует в Telegram → Дзен подхватывает через @zen_sync_bot**.

У Яндекс Дзена **нет публичного API**. Официальный способ — [кросспостинг из Telegram](https://dzen.ru/help/ru/channel/cross-platform.html).

## Схема

```
articles/dzen/*.md
       ↓
queue/publish-queue.yaml  (draft → approved)
       ↓
publish.py → Telegram-канал
       ↓
@zen_sync_bot (Синхробот) → Дзен (2–10 мин)
       ↓
Тизер в @mariyaprodirect (отдельно, вручную или второй канал)
```

## Одноразовая настройка (≈20 мин)

### 1. Telegram-бот

1. [@BotFather](https://t.me/BotFather) → `/newbot` → имя, например `mkekspert_publish_bot`
2. Скопируйте токен → `TELEGRAM_BOT_TOKEN` в `.env`
3. Добавьте бота **администратором** в канал `@mariyaprodirect` (или отдельный канал для статей)

### 2. Синхробот Дзена

1. Дзен Студия → **Настройки** → **Кросспостинг** → **Telegram** → **Получить код доступа**
2. [@zen_sync_bot](https://t.me/zen_sync_bot) → вставить код
3. `/sync` → добавить **zen_sync_bot** админом канала (канал **публичный**)
4. Режим публикации:
   - **Авто** — каждый пост канала уходит в Дзен (удобно для статей)
   - **Вручную** — пересылаете пост боту после проверки (больше контроля)

**Важно для Дзена:**
- Заголовок статьи = **первое предложение** поста (до 140 символов). Скрипт это делает сам.
- Обложка = первая картинка в посте (если текст ≤1024 символов в подписи к фото).
- Длинные статьи (>1024) публикуются текстом; обложку можно добавить в Студии Дзена.

### 3. UTM в Дзене

Студия → Кросспостинг → Telegram → **Изменить значения UTM** (чтобы отличать TG и Дзен в Метрике).

### 4. VK (опционально)

1. [vk.com/apps?act=manage](https://vk.com/apps?act=manage) → создать приложение
2. Получить токен сообщества с правом `wall`
3. `VK_ACCESS_TOKEN`, `VK_GROUP_ID` в `.env`

### 5. Файл .env

```bash
cd автоматизация-контента/automation
cp .env.example .env
# заполнить токены
pip install -r requirements.txt
```

## Ежедневный workflow

```bash
cd автоматизация-контента/automation

# Посмотреть очередь
python publish.py queue list

# Вы согласовали текст в чате →
python publish.py queue approve 7-errors-direct

# Проверка без отправки
python publish.py publish 7-errors-direct --dry-run

# Публикация (DRY_RUN=false в .env или убрать --dry-run)
DRY_RUN=false python publish.py publish 7-errors-direct
```

После публикации:
1. Через 2–10 мин проверить [Студию Дзена](https://dzen.ru/studio)
2. Скопировать ссылку на статью → вписать в `dzen_url` в очереди
3. Опубликовать тизер в @mariyaprodirect (или настроить `TELEGRAM_TEASER_CHANNEL_ID`)

## Команды

| Команда | Действие |
|---------|----------|
| `queue list` | Список материалов |
| `queue approve <id>` | Согласовать |
| `publish <id> --dry-run` | Превью |
| `publish <id>` | Отправить в TG (+ VK если настроено) |
| `format articles/dzen/....md` | Текст как уйдёт в Дзен |

## Ограничения

| Платформа | Лимит |
|-----------|-------|
| Telegram | 4096 символов на пост |
| Дзен заголовок | 140 символов (первое предложение) |
| Подпись к фото в TG | 1024 символа |

## Альтернативы (без своего скрипта)

- **publish-mcp** — MCP для Cursor, TG + VK из чата ([GitHub](https://github.com/devladpopov/publish-mcp))
- **Make.com + Google Sheets** — очередь в таблице, пост в TG по расписанию
- **SMMplanner / Postmypost** — планировщик с поддержкой TG

Наш скрипт проще: очередь в репозитории, согласование одной командой, без подписки на SaaS.
