# Разметка Дзен (dzen.ru/klientyandtrafik)

Источники: [справка Дзена — статья](https://dzen.ru/help/ru/channel/article.html), [RSS/HTML](https://dzen.ru/help/ru/website/rss-modify.html), [синхробот TG](https://dzen.ru/a/Z-alcgz9E2tFQFyN).  
GitHub и промпт: `dzen-github-sources.md`, `dzen-prompt.md`.  
Эталон структуры: [статья Свистушкиной](https://dzen.ru/a/ang5i_6noirlj6-z).

Файлы: `articles/dzen/articles/YYYY-MM-DD-slug.md`

---

## Главное: как публиковать автоматически С разметкой

**`@zen_sync_bot` не переносит жирный, H2 и кликабельные ссылки** — это [официальное ограничение Дзена](https://dzen.ru/help/ru/channel/cross-platform.html), не баг скрипта. Неважно, публичный канал или черновик.

| Способ | Разметка в Дзене | Автомат |
|--------|------------------|---------|
| **RSS + HTML** (`DZEN_PUBLISH_MODE=rss`) | ✅ `<b>`, `<h2>`, `<a>`, обложка | ✅ по расписанию |
| TG → `@zen_sync_bot` (`sync`, ≤1024 зн.) | ❌ plain text | ✅ |

**Рекомендуемый поток:**

```bash
cd automation && DRY_RUN=false python3 publish.py publish dzen penoplast-case
```

1. Скрипт пишет `articles/dzen/feed.xml` с HTML (`content:encoded`)
2. Дзен забирает ленту сам (подключить в Студии **один раз**)
3. Статья появляется с жирным, H2, ссылками и обложкой

**Не слать полный текст в zen_sync-канал** — получите пост без разметки (и отдельное фото при длинном тексте).

### Одноразовая настройка RSS в Студии Дзена

1. Залить `feed.xml` на публичный URL, напр. `https://mkekspert.ru/dzen-feed.xml`  
   (или `DZEN_RSS_DEPLOY_PATH` на сервере + `DZEN_RSS_FEED_URL` в `.env`)
2. Задать `DZEN_COVER_BASE_URL` — публичные URL обложек (≥700 px)
3. Студия Дзена → Настройки → RSS → указать URL ленты
4. `DZEN_RSS_DRAFT=true` — черновики в Студии; `false` — автопубликация

### Переменные `.env`

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `DZEN_PUBLISH_MODE` | `rss` | `rss` или `sync` (только ≤1024, без разметки) |
| `DZEN_RSS_DRAFT` | `true` | `native-draft` в RSS → черновик в Студии |
| `DZEN_RSS_FEED_URL` | `https://mkekspert.ru/dzen-feed.xml` | URL для Дзена |
| `DZEN_COVER_BASE_URL` | — | Публичный путь к `assets/covers/` |
| `DZEN_RSS_DEPLOY_PATH` | — | Куда копировать `feed.xml` на сервере |
| `DZEN_TG_NOTIFY` | `false` | Уведомление в TG (только канал **без** zen_sync) |

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

→ `articles/dzen/html/SLUG.html` (для ручной вставки, если RSS ещё не подключён)

---

## Чеклист перед публикацией

- [ ] `title` ≤ 140 символов
- [ ] ≥ 3 блока H2
- [ ] Ссылки — `[анкор](url)`
- [ ] Обложка готова, `DZEN_COVER_BASE_URL` настроен
- [ ] RSS подключён в Студии (или готов HTML для вставки)
- [ ] После появления в Дзене — `dzen_url` в очереди → тизеры

---

## Не делать

- Публиковать длинные статьи через `@zen_sync_bot` (нет разметки, фото отдельно)
- Слать полный текст в zen_sync-канал при режиме RSS
- Голые URL вместо анкоров
