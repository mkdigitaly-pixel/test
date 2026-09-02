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

## Шаг 5. Дзен (один раз)

1. [dzen.ru/studio](https://dzen.ru/studio)
2. **Настройки** → **Свой сайт**
3. Домен: **`blog.mkekspert.ru`** (не mkekspert.ru)
4. Подтвердить домен (файл или метатег на blog — GitHub Pages)
5. **Настроить трансляцию** → URL: `https://blog.mkekspert.ru/dzen-feed.xml`
6. Отправить на проверку

**Зачем:** Дзен забирает статьи с разметкой автоматически; расписание — у агента.

---

## Что дальше автоматом

| Кто | Действие |
|-----|----------|
| Агент | статья → HTML + feed.xml → push на blog.mkekspert.ru |
| Агент | вт/чт Дзен, тизеры TG/VK |
| Вы | только `ок <id>` на текст |

Основной сайт **mkekspert.ru** на Tilda не меняется.
