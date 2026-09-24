# Разметка Дзен (dzen.ru/klientyandtrafik)

Источники: [справка Дзена — статья](https://dzen.ru/help/ru/channel/article.html), [RSS/HTML](https://dzen.ru/help/ru/website/rss-modify.html), [синхробот TG](https://dzen.ru/a/Z-alcgz9E2tFQFyN).  
GitHub и промпт: `dzen-github-sources.md`, `dzen-prompt.md`.  
Эталон структуры: [статья Свистушкиной](https://dzen.ru/a/ang5i_6noirlj6-z).

Файлы: `articles/dzen/articles/YYYY-MM-DD-slug.md`

---

## Главное: автоматическая публикация С разметкой

**`@zen_sync_bot` не переносит жирный, H2 и ссылки** — только RSS + HTML.

| Способ | Разметка | Автомат |
|--------|----------|---------|
| **RSS + HTML** (`auto` / `rss`) | ✅ | ✅ по расписанию |
| TG → zen_sync (`sync`, ≤1024 зн.) | ❌ | ✅ |

```bash
cd automation && python3 publish.py publish dzen penoplast-case
```

Агент автоматически:
1. Генерирует `articles/dzen/feed.xml` с HTML
2. Деплоит feed + обложки + HTML на **blog.mkekspert.ru** (GitHub Pages)
3. Дзен забирает RSS
4. Подтягивает `dzen_url` → публикует тизеры TG/VK

### Одноразовая настройка (инфраструктура)

1. DNS + GitHub Pages для **blog.mkekspert.ru** — см. `checklists/dzen-rss-tilda.md`
2. RSS в Студии Дзена → `https://blog.mkekspert.ru/dzen-feed.xml`
3. `DZEN_RSS_DRAFT=false` — без ручного клика «опубликовать» в Студии

### Переменные `.env`

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `DZEN_PUBLISH_MODE` | `auto` | `auto` / `rss` / `sync` |
| `DZEN_RSS_DRAFT` | `false` | `false` = автопубликация |
| `DZEN_RSS_DEPLOY_GH_PAGES` | `true` | деплой на blog.mkekspert.ru |
| `DZEN_RSS_FEED_URL` | blog.mkekspert.ru | URL для Дзена |
| `DZEN_URL_POLL_BURST_MINUTES` | `15` | ожидание URL перед тизерами |

Подробнее: `docs/automation-agent.md`

---

## Заголовок = H1 (отдельно от тела)

| Правило | Значение |
|---------|----------|
| Где в файле | YAML `title` / `h1` + **не дублировать** в теле как `#` |
| Лимит | **до 140 символов** |
| Ссылки | **запрещены** в заголовке |

---

## Ссылки (кликабельный анкор)

В markdown: только `[текст](url)`. В RSS/HTML: `<a href="...">анкор</a>` — переносится автоматически.

```
[Бесплатный разбор Яндекс Директ](https://mkekspert.ru/razbor-direct?utm_source=dzen&utm_medium=article&utm_campaign=slug)
```

---

## Структура статьи

- Крючок → `## H2` каждые 300–500 знаков → CTA с анкорами
- `**жирный**` в markdown → `<b>` в RSS
- Таблицы → списки (в markdown)
- Обложка: `assets/covers/{campaign-id}.jpg`

```bash
python3 publish.py format-dzen-html articles/dzen/articles/SLUG.md
```

→ `articles/dzen/html/SLUG.html` (резерв для отладки)

---

## Чеклист (агент)

- [ ] `title` ≤ 140 символов
- [ ] ≥ 3 блока H2, ссылки `[анкор](url)`
- [ ] Обложка в `assets/covers/`
- [ ] `status: approved` в очереди

`dzen_url` и тизеры — автоматически через `schedule`.

---

## Не делать

- Публиковать длинные статьи через `@zen_sync_bot` (нет разметки, фото отдельно)
- Слать полный текст в zen_sync-канал при режиме RSS
- Голые URL вместо анкоров
