# Автоматизация контента mkekspert

## Четыре потока

| Поток | Папка | Куда |
|-------|-------|------|
| Статьи Дзен | `articles/dzen/articles/` | Отдельный TG-канал → Синхробот → Дзен |
| Тизеры TG | `articles/dzen/teasers/tg/` | `@mariyaprodirect` |
| Тизеры VK | `articles/dzen/teasers/vk/` | VK |
| Свой контент | `articles/tg/`, `articles/vk/` | TG и VK отдельно, своя разметка |

Подробно: [`docs/content-channels.md`](docs/content-channels.md)  
Контент-план: [`plan/content-backlog.md`](plan/content-backlog.md) · SEO Дзен: [`plan/dzen-seo-content-plan.md`](plan/dzen-seo-content-plan.md)  
Разметка: [`dzen-markup`](references/dzen-markup.md) · [`dzen-seo-rules`](references/dzen-seo-rules.md) · [`tg-markup`](references/tg-markup.md) · [`vk-markup`](references/vk-markup.md) · [`vc-markup`](references/vc-markup.md)

## Структура

```
автоматизация-контента/
├── articles/
│   ├── dzen/articles/      # полные статьи → DZEN-канал
│   ├── dzen/teasers/tg/    # тизеры → @mariyaprodirect
│   ├── dzen/teasers/vk/    # тизеры → VK
│   ├── tg/                 # посты канала (свой контент)
│   └── vk/                 # посты VK (свой контент)
├── automation/             # publish.py, .env
├── queue/                  # очередь кампаний
└── docs/content-channels.md
```

## Публикация кампании (статья + тизеры)

```bash
cd automation
# 1. Статья только в DZEN-канал
python3 publish.py publish dzen 7-errors-direct

# 2. Ссылку из Студии → dzen_url в queue/publish-queue.yaml

# 3. Тизеры в @mariyaprodirect и VK
python3 publish.py publish teasers 7-errors-direct
```

## Свой пост канала / VK

```bash
python3 publish.py publish tg-post 2026-08-30-penoplast-teaser
python3 publish.py publish vk-post my-slug
```

## Настройка

См. [`automation/README.md`](automation/README.md) и [`checklists/automation-setup.md`](checklists/automation-setup.md)

**Главное:** `@zen_sync_bot` привязать к **новому** каналу (`TELEGRAM_DZEN_CHANNEL_ID`), не к `@mariyaprodirect`.
