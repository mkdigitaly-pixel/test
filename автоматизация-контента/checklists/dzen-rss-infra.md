# RSS на mkekspert.ru — инфраструктура (один раз)

Дзен принимает ленту **только с домена сайта** (`mkekspert.ru`), не с GitHub raw.

Целевой URL: **https://mkekspert.ru/dzen-feed.xml**  
Обложки: **https://mkekspert.ru/dzen-covers/**

## Вариант A — SFTP (предпочтительно)

В `automation/.env`:

```
DZEN_RSS_FEED_URL=https://mkekspert.ru/dzen-feed.xml
DZEN_COVER_BASE_URL=https://mkekspert.ru/dzen-covers
DZEN_SFTP_HOST=...
DZEN_SFTP_USER=...
DZEN_SFTP_PASSWORD=...
DZEN_SFTP_REMOTE_FEED=/dzen-feed.xml
DZEN_SFTP_REMOTE_COVERS=/dzen-covers
```

Деплой:

```bash
cd automation && python3 publish.py dzen-rss setup
```

## Вариант B — DDOS-Guard (прокси на GitHub)

Если сайт за DDOS-Guard, а файлы пушатся в git:

1. Панель DDOS-Guard → сайт mkekspert.ru → **Правила / Редиректы**
2. Путь: `/dzen-feed.xml` → прокси на  
   `https://raw.githubusercontent.com/mkdigitaly-pixel/test/cursor/content-formatting-plan-0a4f/автоматизация-контента/articles/dzen/feed.xml`
3. Путь: `/dzen-covers/*` → прокси на raw GitHub `.../assets/covers/`

После правила — снова `python3 publish.py dzen-rss setup`.

## Подключение в Студии Дзена

1. [dzen.ru/studio](https://dzen.ru/studio) → войти
2. **Настройки** (слева внизу)
3. **Свой сайт** → домен `mkekspert.ru` (подтвердить, если ещё нет)
4. **Настроить трансляцию материалов сайта в Дзен**
5. URL ленты: `https://mkekspert.ru/dzen-feed.xml`
6. Отправить на проверку

Канал: [klientyandtrafik](https://dzen.ru/klientyandtrafik) — нужно ≥10 подписчиков и привязанный сайт.

## Проверка

```bash
curl -sI https://mkekspert.ru/dzen-feed.xml | head -3
# HTTP/2 200

cd automation && python3 publish.py dzen-rss setup
```
