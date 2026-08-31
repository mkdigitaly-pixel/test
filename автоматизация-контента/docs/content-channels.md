# Каналы и разметка контента

## Схема (4 потока)

```
┌─────────────────────────────────────────────────────────────┐
│  articles/dzen/articles/*.md                                │
│  Полные статьи                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ publish → TELEGRAM_DZEN_CHANNEL
                           │ @zen_sync_bot → Дзен (авто)

┌─────────────────────────────────────────────────────────────┐
│  articles/dzen/teasers/tg/*.md                              │
│  Тизеры «читайте на Дзен» + ссылка                          │
└──────────────────────────┬──────────────────────────────────┘
                           │ publish → TELEGRAM_MAIN_CHANNEL
                           │ @mariyaprodirect (НЕ уходит в Дзен)

┌─────────────────────────────────────────────────────────────┐
│  articles/dzen/teasers/vk/*.md                              │
│  Тизеры для VK со ссылкой на Дзен                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ publish → VK

┌─────────────────────────────────────────────────────────────┐
│  articles/tg/*.md          │  articles/vk/*.md               │
│  Свой контент канала       │  Тот же смысл, разметка VK     │
└──────────────────────────┬──────────────────────────────────┘
                           │ вручную / отдельная очередь
                           │ НЕ в канал Дзена
```

## Каналы Telegram

| Переменная `.env` | Куда | Что публикуем |
|-------------------|------|----------------|
| `TELEGRAM_DZEN_CHANNEL_ID` | **Отдельный канал** только для Дзена | Полные статьи из `dzen/articles/` |
| `TELEGRAM_MAIN_CHANNEL_ID` | `@mariyaprodirect` | Свои посты + тизеры на Дзен |

**Важно:** `@zen_sync_bot` привязать только к **DZEN-каналу**, не к `@mariyaprodirect`.

## Файлы по типам

| Папка | Назначение | Правила разметки |
|-------|------------|------------------|
| `articles/dzen/articles/` | Статья для Дзена | `references/dzen-markup.md` |
| `articles/dzen/teasers/tg/` | Тизер в основной TG | `references/tg-markup.md` |
| `articles/dzen/teasers/vk/` | Тизер в VK | `references/vk-markup.md` |
| `articles/tg/` | Посты канала (свой контент) | `references/tg-markup.md` |
| `articles/vk/` | Посты VK (свой контент) | `references/vk-markup.md` |
| `articles/vc/` | Черновики под VC.ru | `references/vc-markup.md` (ручная публикация) |

Голос и запреты: `maria-voice.md`, `banned-phrases.md`.  
Контент-план на согласование: `plan/content-backlog.md`.

## Очереди публикации

**Кампании Дзен** (статья + тизеры) → `queue/publish-queue.yaml`  
**Свои посты TG/VK** → `queue/posts-queue.yaml`

Согласование для обеих: `ок <id>` → `python publish.py queue approve <id>`

### Кампания Дзен

```yaml
- id: 7-errors-direct
  status: draft
  dzen_article: articles/dzen/articles/2026-08-30-7-errors-direct.md
  dzen_teaser_tg: articles/dzen/teasers/tg/2026-08-30-7-errors.md
  dzen_teaser_vk: articles/dzen/teasers/vk/2026-08-30-7-errors.md
  cover: assets/covers/7-errors-direct.jpg
  dzen_url: ""
```

### Свой пост TG или VK

```yaml
- id: tg-5-errors-reminder
  platform: tg          # tg | vk
  status: approved
  post: articles/tg/tg-5-errors-reminder.md
  cover: assets/covers/tg-5-errors-reminder.jpg
  cover_headline: "7 ошибок в Директе"
  cover_subline: "Заявок нет?"
```

Посты **только для TG** или **только для VK** — отдельные файлы в `articles/tg/` и `articles/vk/`.  
Автопубликация по расписанию: среда 11:00 TG, пятница 11:00 VK — см. `queue/posting-schedule.yaml`.

## Порядок публикации кампании

1. `publish dzen <id>` — статья в DZEN-канал → ждём ссылку в Студии
2. Вписать `dzen_url` в очередь
3. `publish teasers <id>` — тизеры в @mariyaprodirect и VK (с картинкой)

## Настройка нового DZEN-канала

1. Создать **публичный** канал, например `@mkekspert_dzen` или `@klientyandtrafik_tg`
2. Добавить `@Dzenkovalevabot` и `@zen_sync_bot` админами
3. В Дзен Студии: `/restart` в синхроботе → привязать **новый** канал (отвязать `@mariyaprodirect`)
4. `TELEGRAM_DZEN_CHANNEL_ID=@новый_канал` в `.env`
