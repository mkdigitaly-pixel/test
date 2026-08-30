# Чеклист: каналы и автопубликация

## Разделение каналов (обязательно)

- [ ] Создан **отдельный публичный** TG-канал для статей Дзен
- [ ] `@Dzenkovalevabot` — админ в **обоих** каналах
- [ ] `@zen_sync_bot` — админ только в **DZEN-канале**
- [ ] В синхроботе `/restart` → привязан **DZEN-канал**, `@mariyaprodirect` **отвязан**
- [ ] `.env`: `TELEGRAM_MAIN_CHANNEL_ID=@mariyaprodirect`
- [ ] `.env`: `TELEGRAM_DZEN_CHANNEL_ID=@ваш_dzen_канал`

## Бот

- [ ] Токен в `automation/.env`
- [ ] Тест: `python3 publish.py publish dzen <id> --dry-run` — канал DZEN, не mariyaprodirect

## Первая кампания по новой схеме

- [ ] `publish dzen` → статья только в DZEN-канале
- [ ] Ссылка в Студии → `dzen_url` в очереди
- [ ] `publish teasers` → тизер в @mariyaprodirect + VK (с обложкой)

## Свой контент TG / VK

- [ ] Посты в `articles/tg/` и `articles/vk/` — разные файлы
- [ ] `publish tg-post` / `publish vk-post` — не попадают в Дзен
