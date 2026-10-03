# Дзен — источники правил и разметки (GitHub + официальная справка)

Подборка для агента и автора. Берём **структуру и HTML-ограничения**, не копируем чужие тексты.

## Официальная справка Дзена

| Документ | URL | Что брать |
|----------|-----|-----------|
| Статья в редакторе | https://dzen.ru/help/ru/channel/article.html | H2/H3, жирный, гиперссылки, обложка, оглавление |
| RSS / HTML | https://dzen.ru/help/ru/website/rss-modify.html | `content:encoded`, whitelist тегов, `enclosure`, `guid` |
| Требования к контенту | https://dzen.ru/help/ru/requirements/content_requirements.html | модерация, запреты |
| Синхробот TG | https://dzen.ru/a/Z-alcgz9E2tFQFyN | лимит 140 символов заголовка, фото = обложка, **форматирование из TG не переносится** |

## Лучшие репозитории на GitHub

### 1. [Bormotoon/dzen-rss-feed](https://github.com/Bormotoon/dzen-rss-feed) — главный ориентир

Актуальный WordPress-плагин под спецификацию 2025–2026.

- Спека в репо: [`docs/dzen-rss-spec.md`](https://github.com/Bormotoon/dzen-rss-feed/blob/main/docs/dzen-rss-spec.md)
- Whitelist HTML: `p`, `a`, `b`, `i`, `u`, `s`, `h1`–`h4`, `blockquote`, `ul/ol`+`li`, `figure`, `figcaption`, `img`
- Обложка: `enclosure` + дубль первым `<p><img>` в теле, ширина ≥ 700 px
- `category`: `format-article`, `index`, `comment-none`
- Стабильный `guid` — без дублей при правках

### 2. [konrad-molitor/zen-feed](https://github.com/konrad-molitor/zen-feed)

Express middleware под [официальный RSS](https://yandex.ru/support/zen/website/rss-modify.html).

- Санитайзер: только разрешённые теги, `strong`→`b`, `em`→`i`
- `enclosure` — URL **всех** картинок из статьи
- Полезно как эталон «что вырезать из HTML»

### 3. [eugenekrukov/zhekich-feed-generator-for-dzen](https://github.com/eugenekrukov/zhekich-feed-generator-for-dzen)

Плагин под единый RSS-формат Дзена (2026).

- Тот же whitelist HTML
- `em`→`i`, `strong`→`b`, `br`→абзацы
- Обложка ≥ 700 px

### 4. Прочее (справочно)

| Репо | Зачем смотреть |
|------|----------------|
| [why-me-why-not/yandexzen-post-articles](https://github.com/why-me-why-not/yandexzen-post-articles) | Selenium-постинг (риск бана, **не используем**) |
| [LukaS0lncev/NT-157](https://github.com/LukaS0lncev/NT-157) | Старый WP RSS, типичные ошибки валидации |

## Эталон вёрстки (конкурент / ниша Директ)

**Пример:** [Что входит в работу с Директ — кроме настройки](https://dzen.ru/a/ang5i_6noirlj6-z) (Татьяна Свистушкина).

Что взять для mkekspert (без копирования текста и без эмодзи в H2 — см. `maria-voice.md`):

| Приём | Как у эталона | Как у Марии |
|-------|---------------|-------------|
| H2 | каждые 300–500 знаков, одна мысль | `##` в markdown → H2 в Студии |
| H3 | подтезис внутри блока | `###` при необходимости |
| Абзацы | короткие, 1–3 предложения | так же |
| Цитата | `>` для реплики клиента | блокquote в HTML |
| Ссылки | **анкорный текст**, не URL в строке («Написать в WA», не `https://…`) | `[Бесплатный разбор](url)` |
| CTA | в конце, 1–2 кликабельные ссылки | razbor-direct + TG |
| Списки | тире или маркированный список | `—` в markdown |

## Два пути публикации в проекте

| Путь | Формат | Разметка |
|------|--------|----------|
| **RSS** (`DZEN_PUBLISH_MODE=rss`) | HTML в `content:encoded` | ✅ жирный, H2, ссылки, обложка — автомат |
| TG → `@zen_sync_bot` (`sync`, ≤1024) | plain text | ❌ только текст, без разметки |

Команда HTML для Студии:

```bash
cd automation
python3 publish.py format-dzen-html articles/dzen/articles/2026-08-30-penoplast-case.md
```

Файл: `articles/dzen/html/{slug}.html`
