# Автопубликация

## Два канала Telegram

| Канал | .env | Содержимое | Синхробот |
|-------|------|------------|-----------|
| `@mariyaprodirect` | `TELEGRAM_MAIN_CHANNEL_ID` | Свои посты + тизеры на Дзен | **НЕТ** |
| Новый канал | `TELEGRAM_DZEN_CHANNEL_ID` | Только полные статьи | **ДА** |

## Настройка DZEN-канала

1. Создать публичный канал (например `@mkekspert_dzen`)
2. `@Dzenkovalevabot` — админ (публикация)
3. В [@zen_sync_bot](https://t.me/zen_sync_bot): `/restart` → привязать **новый** канал (отвязать `@mariyaprodirect`)
4. `TELEGRAM_DZEN_CHANNEL_ID=@ваш_dzen_канал` в `.env`

## Порядок кампании

1. Согласование: `queue approve <id>` или `ок <id>` в чате
2. **Автомат** по `posting-schedule.yaml` — `schedule run` / `run-schedule.sh`
3. `dzen_url` подтягивается из API Дзена (`schedule sync-urls`)

Подробно: [`docs/automation-agent.md`](../docs/automation-agent.md)

## Команды

```bash
python3 publish.py queue approve <id>
./run-schedule.sh                    # сегодня + просроченные (catch-up)
python3 publish.py schedule list
python3 publish.py publish dzen <id> [--dry-run]      # вручную
python3 publish.py publish teasers <id>
python3 publish.py publish tg-post <slug>
python3 publish.py publish vk-post <slug>
```

## SEO-органика

```bash
python3 seo_pipeline.py audit
python3 seo_pipeline.py keywords list
python3 seo_pipeline.py status
python3 seo_pipeline.py report
```

Документ: [`docs/seo-pipeline.md`](../docs/seo-pipeline.md) · чеклист: [`checklists/seo-stack.md`](../checklists/seo-stack.md)

`schedule run` без `--date` выполняет **сегодня и все просроченные** слоты. Без `AUTO_PUBLISH=true` — dry-run, статусы не трогает.
