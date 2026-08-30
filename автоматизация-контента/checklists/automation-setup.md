# Чеклист: первый запуск автопубликации

Отмечайте по мере выполнения.

## Telegram + Дзен

- [ ] Создан бот в @BotFather, токен в `automation/.env`
- [ ] Бот добавлен админом в канал `@mariyaprodirect` (или отдельный канал для статей)
- [ ] В Дзен Студии получен код кросспостинга
- [ ] @zen_sync_bot авторизован, выполнен `/sync`
- [ ] zen_sync_bot — админ канала
- [ ] Выбран режим: авто или вручную (`/changemode`)
- [ ] В Студии настроены UTM для кросспостинга
- [ ] Тест: короткий пост в канал → появился в Дзене за 10 мин

## Скрипт

- [ ] `pip install -r automation/requirements.txt`
- [ ] `cp automation/.env.example automation/.env` — токены заполнены
- [ ] `python publish.py publish 7-errors-direct --dry-run` — текст ок
- [ ] `queue approve` → `DRY_RUN=false publish` — первая статья

## VK (опционально)

- [ ] Токен сообщества с правом wall
- [ ] `VK_ACCESS_TOKEN`, `VK_GROUP_ID` в `.env`

## После первой публикации

- [ ] Ссылка на статью Дзен → `dzen_url` в `queue/publish-queue.yaml`
- [ ] Тизер в @mariyaprodirect со ссылкой
- [ ] Пост VK (скрипт или вручную)
