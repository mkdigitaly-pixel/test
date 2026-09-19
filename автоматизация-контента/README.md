# Автоматизация контента mkekspert

## Четыре потока

| Поток | Папка | Куда |
|-------|-------|------|
| Статьи Дзен | `articles/dzen/articles/` | Отдельный TG-канал → Синхробот → Дзен |
| Тизеры TG | `articles/dzen/teasers/tg/` | `@mariyaprodirect` |
| Тизеры VK | `articles/dzen/teasers/vk/` | VK |
| Свой контент | `articles/tg/`, `articles/vk/` | TG и VK отдельно, своя разметка |

Подробно: [`docs/content-channels.md`](docs/content-channels.md)  
**SEO-органика (стек):** [`docs/seo-pipeline.md`](docs/seo-pipeline.md) · чеклист [`checklists/seo-stack.md`](checklists/seo-stack.md) · банк ключей `seo/keywords.yaml`  
Контент-план: [`plan/content-backlog.md`](plan/content-backlog.md) · SEO Дзен: [`plan/dzen-seo-content-plan.md`](plan/dzen-seo-content-plan.md) · **Расписание:** [`plan/posting-schedule.md`](plan/posting-schedule.md)  
**Поиск тем и рерайт:** [`references/topic-research.md`](references/topic-research.md) · бэклог: [`plan/topic-sources-backlog.md`](plan/topic-sources-backlog.md)  
Разметка: [`dzen-markup`](references/dzen-markup.md) · [`dzen-prompt`](references/dzen-prompt.md) · [`dzen-github-sources`](references/dzen-github-sources.md) · [`dzen-seo-rules`](references/dzen-seo-rules.md) · [`tg-markup`](references/tg-markup.md) · [`vk-markup`](references/vk-markup.md) · [`vc-markup`](references/vc-markup.md)

## Структура

```
автоматизация-контента/
├── articles/
│   ├── dzen/articles/      # полные статьи → DZEN-канал
│   ├── dzen/teasers/tg/    # тизеры → @mariyaprodirect
│   ├── dzen/teasers/vk/    # тизеры → VK
│   ├── tg/                 # посты канала (свой контент)
│   └── vk/                 # посты VK (свой контент)
├── automation/             # publish.py, seo_pipeline.py, .env
├── seo/                    # ключи, позиции, отчёты (органика)
├── queue/                  # очередь кампаний
└── docs/seo-pipeline.md    # SEO-стек
```

## Блог на Tilda (витрина)

Стиль blog.mkekspert.ru = палитра сайта. Блок для вставки в Tilda:

```bash
cd automation
python3 export_tilda_blog.py   # → content/tilda-blog-block.html
```

Инструкция: [`content/tilda-blog-page.md`](content/tilda-blog-page.md)

## SEO-органика

```bash
cd automation
python3 seo_pipeline.py audit      # готовность Tilda + blog
python3 seo_pipeline.py status     # воронка ключей
python3 seo_pipeline.py report     # недельный отчёт
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
