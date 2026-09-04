# Автопубликация — Cloud Agent

Всё по расписанию делает **агент**. Ручных шагов на каждую статью нет.

## Поток (полностью автоматический)

```
ок <id>  →  approved
    ↓
вт/чт 10:00  publish_dzen
    ├─ HTML + feed.xml
    ├─ gh-pages → blog.mkekspert.ru
    └─ Дзен забирает ленту
    ↓
schedule sync-urls + poll  →  dzen_url в очередь
    ↓
вт/чт 12:00  publish_teasers
    ├─ TG @mariyaprodirect + обложка
    └─ VK klientyandtrafik + обложка 1:1
```

**Ср 11:00** — свой пост TG. **Пт 11:00** — свой пост VK.

Если `dzen_url` ещё не появился — слот тизеров остаётся `pending`, cron повторяет до успеха.

## Что делает 👤 Мария

1. Согласовать текст: **`ок <id>`** (агент ставит `approved`)
2. По желанию — проверить посты в каналах

Всё остальное — агент.

## Инфраструктура (один раз, не на каждую статью)

Настраивается в `.env` и Студии Дзена при первом запуске:

| Что | Кто | Когда |
|-----|-----|-------|
| `.env` — токены TG/VK, `AUTO_PUBLISH=true` | агент / env-setup | один раз |
| RSS-лента в Студии Дзена | один раз по `checklists/dzen-rss-tilda.md` (blog.mkekspert.ru) |
| `VK_USER_TOKEN` для обложек | агент / vkhost | один раз |

**mkekspert.ru** остаётся на Tilda. Статьи и RSS — на **blog.mkekspert.ru** (GitHub Pages). Инструкция: `checklists/dzen-rss-tilda.md`.

## `.env` (ключевые)

```
AUTO_PUBLISH=true
DZEN_PUBLISH_MODE=auto
DZEN_RSS_DRAFT=false          # автопубликация, без клика в Студии
DZEN_RSS_DEPLOY_GH_PAGES=true # blog.mkekspert.ru после каждой статьи
```

Полный шаблон: `automation/.env.example`

## Команды (агент / отладка)

```bash
cd automation
./run-schedule.sh
python3 publish.py schedule list
python3 publish.py schedule sync-urls
python3 publish.py schedule run --date 2026-09-02 --force
```

## Таймер

Cron UTC `0 7,8,9,10,11 * * *` → 10:00–14:00 МСК: обложки, sync-urls, слоты, повтор pending.

Расписание: `plan/posting-schedule.md`

## Исключения (вне автопостинга)

- **VC.ru** — отдельный контур, слоты `vc_manual` пропускаются
- **Закреп TG** — отдельная команда, не в расписании
