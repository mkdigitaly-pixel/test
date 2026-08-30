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

## Команды

```bash
python3 publish.py queue approve <id>
python3 publish.py publish dzen <id> [--dry-run]      # статья → DZEN-канал
python3 publish.py publish teasers <id>                 # тизеры → TG + VK
python3 publish.py publish tg-post <slug>             # свой пост → mariyaprodirect
python3 publish.py publish vk-post <slug>             # свой пост → VK
```

Скрипт **не даст** опубликовать статью в тот же канал, что и основной (`dzen` + совпадающие ID).

## Порядок кампании

1. `publish dzen` → ждём статью в Студии
2. `dzen_url` в `queue/publish-queue.yaml`
3. `publish teasers` → короткий пост с картинкой в @mariyaprodirect + VK

Полная схема: [`../docs/content-channels.md`](../docs/content-channels.md)
