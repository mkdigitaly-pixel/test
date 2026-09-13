# VK: картинка к посту

Новые посты уходят **с обложкой** по ключу сообщества (`VK_ACCESS_TOKEN`):
загрузка через `photos.getMessagesUploadServer` → `wall.post` с `attachments`.

`photos.getWallUploadServer` с ключом сообщества даёт error 27 — это ограничение VK.
Редактировать уже вышедший пост (`wall.edit`) ключ сообщества тоже не умеет.

## Что нужно в `.env`

```
VK_ACCESS_TOKEN=ключ сообщества (стена + фотографии)
VK_GROUP_ID=222121025
```

`VK_USER_TOKEN` больше не обязателен. Старый пост без картинки — прикрепите фото вручную в интерфейсе VK.

## Проверка

```bash
cd automation
python3 publish.py publish vk-post vk-week2 --dry-run
```

Должно быть `(текст+фото)`.
