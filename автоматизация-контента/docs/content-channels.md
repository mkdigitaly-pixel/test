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

| Папка | Назначение | Разметка |
|-------|------------|----------|
| `articles/dzen/articles/` | Статья для Дзена | Заголовок, ##, plain text для синхробота |
| `articles/dzen/teasers/tg/` | Тизер в основной TG | Тире, коротко, ссылка на Дзен |
| `articles/dzen/teasers/vk/` | Тизер в VK | Абзацы, эмодзи умеренно, ссылка |
| `articles/tg/` | Посты канала | Свой стиль TG, без привязки к Дзен |
| `articles/vk/` | Посты VK | Отдельный текст, не копипаст из TG |

## Очередь публикации

Один материал (кампания) = одна запись в `queue/publish-queue.yaml`:

```yaml
- id: 7-errors-direct
  status: draft
  dzen_article: articles/dzen/articles/2026-08-30-7-errors-direct.md
  dzen_teaser_tg: articles/dzen/teasers/tg/2026-08-30-7-errors.md
  dzen_teaser_vk: articles/dzen/teasers/vk/2026-08-30-7-errors.md
  cover: assets/covers/7-errors-direct.jpg
  dzen_url: ""   # после появления статьи в Дзене
```

Посты **только для TG-канала** или **только для VK** — отдельные файлы в `articles/tg/` и `articles/vk/`, публикуются отдельно (`publish tg-post …` / `publish vk-post …`).

## Порядок публикации кампании

1. `publish dzen <id>` — статья в DZEN-канал → ждём ссылку в Студии
2. Вписать `dzen_url` в очередь
3. `publish teasers <id>` — тизеры в @mariyaprodirect и VK (с картинкой)

## Настройка нового DZEN-канала

1. Создать **публичный** канал, например `@mkekspert_dzen` или `@klientyandtrafik_tg`
2. Добавить `@Dzenkovalevabot` и `@zen_sync_bot` админами
3. В Дзен Студии: `/restart` в синхроботе → привязать **новый** канал (отвязать `@mariyaprodirect`)
4. `TELEGRAM_DZEN_CHANNEL_ID=@новый_канал` в `.env`
