# Автопубликация — Cloud Agent

Публикацию по расписанию выполняет **агент**, не вручную.

## Как это работает

1. Контент согласован → `status: approved` в `queue/publish-queue.yaml` (Дзен) или `queue/posts-queue.yaml` (свои TG/VK)
2. **Агент** генерирует яркие обложки и кладёт в `assets/covers/` (ключ OpenAI вам не нужен)
3. Слоты в `queue/posting-schedule.yaml`:
   - **вт/чт 10:00** — Дзен, **12:00** — тизеры TG + VK
   - **ср 11:00** — свой пост TG (`articles/tg/`)
   - **пт 11:00** — свой пост VK (`articles/vk/`)
4. **Темы** — анализ Promopult, Click.ru, Habr → структура + рерайт (`references/topic-research.md`)
4. Таймер Cloud Agent запускает `automation/run-schedule.sh` несколько раз в день (МСК)
5. Скрипт:
   - создаёт обложки, если файлов ещё нет
   - подтягивает `dzen_url` из API Дзена по заголовку статьи
   - публикует просроченные слоты на сегодня **с фото** (Дзен, тизеры TG+VK, свои посты TG/VK)
   - тизеры повторяет, если ссылка ещё не появилась (`pending`)

## Настройка `.env`

```
AUTO_PUBLISH=true
DRY_RUN=true
DZEN_PUBLISH_MODE=rss          # автомат с разметкой (не zen_sync)
DZEN_RSS_FEED_URL=https://mkekspert.ru/dzen-feed.xml
DZEN_COVER_BASE_URL=...        # публичные URL обложек
```

**Дзен:** RSS-лента (`feed.xml`) — единственный автоматический путь с жирным/H2/ссылками.  
`@zen_sync_bot` разметку не переносит (официально). Подключить RSS в Студии один раз → `references/dzen-markup.md`.

`OPENAI_API_KEY` — не обязателен.

## Команды (для агента / отладки)

```bash
cd automation
./run-schedule.sh              # полный цикл на сегодня
python3 publish.py schedule list
python3 publish.py schedule sync-urls
python3 publish.py schedule run --dry-run
python3 publish.py schedule run --date 2026-09-02 --force
```

## Что делает 👤 Мария

- Согласовать текст: `ок <id>`
- Проверять результат в каналах (по желанию)
- VC.ru — вручную по слотам в расписании

Всё остальное — автомат.

## Таймер агента

Cron UTC `0 7,8,9,10,11 * * *` → 10:00–14:00 МСК, покрывает слоты и повтор тизеров.

Расписание: `plan/posting-schedule.md`
