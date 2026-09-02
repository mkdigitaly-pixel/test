# RSS для Дзена — сайт на Tilda (mkekspert.ru)

**Сайт:** Tilda, домен `mkekspert.ru`, перед сайтом **DDOS-Guard** (в ответе сервера: `server: ddos-guard`).

## Почему не через Tilda и не SFTP

| Способ | Работает? |
|--------|-----------|
| Загрузить `dzen-feed.xml` в Tilda | **Нет** — в корень можно только `robots.txt` и `sitemap.xml` |
| SFTP на `mkekspert.ru` | **Нет** — у Tilda нет FTP к вашему домену |
| Страница Tilda с XML в Zero Block | **Нет** — отдаётся HTML, не RSS |
| **DDOS-Guard: путь на GitHub** | **Да** — один раз в панели, дальше всё автоматом |

Дзен принимает ленту **только с домена сайта**. В Студии указываете:

`https://mkekspert.ru/dzen-feed.xml`

Файл лежит в git, а DDOS-Guard отдаёт его по этому адресу.

---

## Роли

| Кто | Что |
|-----|-----|
| **Агент** | Пишет `feed.xml`, обложки, `git push`, проверяет URL, подключает RSS в Студии (если вы вошли в Дзен) |
| **Вы (один раз)** | Правило в DDOS-Guard + подтверждение сайта в Дзене (метатег в Tilda) |

---

## Часть 1. DDOS-Guard (≈10 мин, один раз)

### 1.1. Войти в панель

1. [ddos-guard.ru](https://ddos-guard.ru) → **Личный кабинет**
2. **Защита сайтов** (или «Web protection»)
3. Выбрать домен **mkekspert.ru**

### 1.2. Правило для ленты RSS

1. Слева: **Правила защиты** (L7)
2. **Добавить правило**
3. Заполнить:

| Поле | Значение |
|------|----------|
| **Условие 1** | URL → **равен** → `/dzen-feed.xml` |
| **Действие** | **Редирект** (код **302** или **307**) |
| **URL назначения** | см. ниже |

**URL файла ленты** (после merge в `main`):

```
https://raw.githubusercontent.com/mkdigitaly-pixel/test/main/автоматизация-контента/articles/dzen/feed.xml
```

Пока PR не влит — подставьте ветку из репозитория, например:

```
https://raw.githubusercontent.com/mkdigitaly-pixel/test/cursor/content-formatting-plan-0a4f/автоматизация-контента/articles/dzen/feed.xml
```

4. **Приоритет** — выше общих правил (чтобы сработало до Tilda)
5. **Сохранить** / включить правило

### 1.3. Правило для обложек (рекомендуется)

Второе правило:

| Поле | Значение |
|------|----------|
| **Условие** | URL **начинается с** `/dzen-covers/` |
| **Действие** | Редирект на GitHub raw, путь к файлу |

Пример для файла `penoplast-case.jpg`:

```
https://raw.githubusercontent.com/mkdigitaly-pixel/test/main/автоматизация-контента/assets/covers/penoplast-case.jpg
```

Если в панели есть **прокси / подмена origin** вместо редиректа — лучше прокси (URL в браузере остаётся `mkekspert.ru`). Редирект 302 на практике у большинства тоже проходит проверку Дзена.

### 1.4. Проверка

В терминале или в браузере:

```text
https://mkekspert.ru/dzen-feed.xml
```

Должен открыться XML с `<rss` и `<item>`, **не** страница 404 Tilda.

```bash
curl -sI "https://mkekspert.ru/dzen-feed.xml" | head -5
```

Ожидание: `HTTP/2 200` или `302` с переходом на raw GitHub.

Напишите агенту: **«готово DDOS-Guard»** — он запустит `publish.py dzen-rss setup` и проверит ленту.

---

## Часть 2. Tilda — подтверждение сайта в Дзене

Если домен в Дзене ещё не подтверждён:

1. **Tilda** → проект mkekspert → **Настройки сайта** → **SEO**
2. Блок **Дополнительный HTML-код** → вкладка **В `<head>`**
3. Вставить метатег / файл, который даст **Студия Дзена** → **Свой сайт** → **Подтвердить**
4. **Сохранить** и **Опубликовать** сайт в Tilda

Без публикации Tilda метатег на живом сайте не появится.

---

## Часть 3. Студия Дзена — подключить RSS (один раз)

1. [dzen.ru/studio](https://dzen.ru/studio) → канал [klientyandtrafik](https://dzen.ru/klientyandtrafik)
2. **Настройки** (иконка шестерёнки, слева внизу)
3. **Свой сайт** (не раздел «Лента» в настройках чтения!)
4. Домен: **mkekspert.ru** — подтвердить, если нужно
5. **Настроить трансляцию материалов сайта в Дзен**
6. URL RSS: `https://mkekspert.ru/dzen-feed.xml`
7. **Отправить на проверку**

Условия Дзена: **≥10 подписчиков** на канале, сайт подтверждён, в ленте **≥10 материалов** (агент собирает автоматически).

После одобрения новые статьи из git попадают в Дзен по расписанию — **без ручной вставки HTML**.

---

## Часть 4. Что делает агент дальше (автоматически)

```bash
cd автоматизация-контента/automation
python3 publish.py dzen-rss setup    # пересборка feed + проверка URL
./run-schedule.sh                    # вт/чт Дзен + тизеры
```

В `.env` уже должно быть:

```env
DZEN_RSS_FEED_URL=https://mkekspert.ru/dzen-feed.xml
DZEN_COVER_BASE_URL=https://mkekspert.ru/dzen-covers
DZEN_RSS_DRAFT=false
DZEN_RSS_DEPLOY_GIT=true
AUTO_PUBLISH=true
```

**SFTP не нужен** для Tilda.

---

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| В Дзене вставили URL GitHub raw | Только `https://mkekspert.ru/dzen-feed.xml` |
| Искали RSS в «Лента» настроек | Нужно: **Настройки → Свой сайт → трансляция** |
| 404 на `/dzen-feed.xml` | Нет правила DDOS-Guard или неверный URL в редиректе |
| Дзен отклонил ленту | Меньше 10 item, нет `content:encoded`, обложка &lt;700 px — агент пересоберёт: `dzen-rss setup` |
| Статьи без жирного/H2 | Подключён zen_sync вместо RSS — оставить только RSS |

---

## Ссылки

- [Объединение сайта и канала (Дзен)](https://dzen.ru/help/ru/website/site-to-channel.html)
- [Разметка RSS (Дзен)](https://dzen.ru/help/ru/website/rss-modify.html)
- [Правила защиты DDOS-Guard](https://ddos-guard.ru/tutorials/website-protection/protection-rules)
