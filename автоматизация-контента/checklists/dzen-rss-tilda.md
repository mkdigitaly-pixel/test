# RSS → Дзен: автомат статей (сайт на Tilda)

**mkekspert.ru** на Tilda — визитка. **Автомат статей** — на поддомене **blog.mkekspert.ru** (не Tilda, файлы из git).

---

## Шаг 1. Поддомен в DNS

Где управляется домен **mkekspert.ru** (Tilda → Настройки сайта → Домен, или регистратор):

| Тип | Имя | Значение |
|-----|-----|----------|
| CNAME | `blog` | `mkdigitaly-pixel.github.io` |

(точное значение даст GitHub после шага 2)

**Зачем:** отдельный адрес только для статей и RSS; Tilda трогать не нужно.

---

## Шаг 2. GitHub Pages

1. Репозиторий `mkdigitaly-pixel/test` → **Settings** → **Pages**
2. Source: ветка **`gh-pages`**, папка `/` (root)
3. Custom domain: **`blog.mkekspert.ru`**
4. Включить **Enforce HTTPS**

**Зачем:** бесплатный хостинг для `dzen-feed.xml`, обложек и HTML статей. Агент пушит файлы сам.

---

## Шаг 3. Переменные (агент / `.env`)

```
DZEN_RSS_SITE_URL=https://blog.mkekspert.ru
DZEN_RSS_FEED_URL=https://blog.mkekspert.ru/dzen-feed.xml
DZEN_COVER_BASE_URL=https://blog.mkekspert.ru/covers
DZEN_RSS_DEPLOY_GH_PAGES=true
```

Команда агента: `python3 publish.py dzen-rss setup`

**Зачем:** лента и ссылки в RSS ведут на `blog.mkekspert.ru`, не на Tilda.

---

## Шаг 4. Проверка

Открыть: **https://blog.mkekspert.ru/dzen-feed.xml** — XML, не ошибка.

---

## Шаг 5. Дзен: подтвердить домен (один раз)

1. [dzen.ru/studio](https://dzen.ru/studio) → **Настройки** → **Свой сайт**
2. Домен: **`blog.mkekspert.ru`** (не mkekspert.ru)
3. Выберите способ подтверждения:

### Способ А — метатег (удобнее)

Дзен покажет что-то вроде:

```html
<meta name="yandex-verification" content="XXXXXXXXXXXX" />
```

**Пришлите агенту** значение `content` (или весь тег) — агент пропишет в `.env`:

```
DZEN_YANDEX_VERIFICATION=XXXXXXXXXXXX
```

и выполнит `python3 publish.py dzen-rss setup`.  
Проверка: https://blog.mkekspert.ru/ — в исходном коде страницы должен быть метатег.  
Затем в Студии нажмите **Подтвердить**.

### Способ Б — HTML-файл

Дзен даст имя файла, например `yandex_XXXXXXXX.html`, и содержимое.

Сохраните файл в:

`автоматизация-контента/articles/dzen/blog-site/yandex_XXXXXXXX.html`

Агент задеплоит → откроется `https://blog.mkekspert.ru/yandex_XXXXXXXX.html` → в Студии **Подтвердить**.

---

## Шаг 6. RSS в Дзене

1. После подтверждения домена → **Настроить трансляцию**
2. URL: `https://blog.mkekspert.ru/dzen-feed.xml`
3. Отправить на проверку

Статус заявки смотрите в **Свой сайт**. Обычно проверка разметки ленты занимает **несколько дней**.

Пока ждёте — ничего менять не нужно: лента и статьи уже на `blog.mkekspert.ru`. После одобрения Дзен начнёт забирать материалы сам; агент публикует по расписанию (`publish dzen` → обновление feed).

**Зачем:** Дзен забирает статьи с разметкой автоматически; расписание — у агента.

---

## Что дальше автоматом

| Кто | Действие |
|-----|----------|
| Агент | статья → HTML + feed.xml → push на blog.mkekspert.ru |
| Агент | вт/чт Дзен, тизеры TG/VK |
| Вы | только `ок <id>` на текст |

Основной сайт **mkekspert.ru** на Tilda не меняется.
