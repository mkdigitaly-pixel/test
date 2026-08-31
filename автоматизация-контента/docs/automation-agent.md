# Автопубликация — Cloud Agent

Публикацию по расписанию выполняет **агент**, не вручную.

## Как это работает

1. Контент согласован → `status: approved` в `queue/publish-queue.yaml`
2. Слоты в `queue/posting-schedule.yaml` (вт/чт 10:00 Дзен, 12:00 тизеры, ср TG, пт VK)
3. Таймер Cloud Agent запускает `automation/run-schedule.sh` несколько раз в день (МСК)
4. Скрипт:
   - подтягивает `dzen_url` из API Дзена по заголовку статьи
   - публикует просроченные слоты на сегодня
   - тизеры повторяет, если ссылка ещё не появилась (`pending`)

## Настройка `.env`

```
AUTO_PUBLISH=true    # расписание публикует по-настоящему
DRY_RUN=true         # ручные команды publish — по-прежнему dry-run, если не DRY_RUN=false
```

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
