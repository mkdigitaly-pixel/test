# VK: картинка к посту

Ключ сообщества публикует текст, но **не загружает новое фото**.

Старый `VK_USER_TOKEN` жил в облачном агенте «Автоматизация контента»,
на этом VPS его **никогда не было** (в git тоже нет). VK Admin на vkhost
сейчас **заблокирован** — токен от него, скорее всего, уже мёртв.

## Получить ключ заново (как раньше, другое приложение)

Не 54768786 — у него Security Error. Берём **Kate Mobile** (приложение живое):

https://oauth.vk.com/authorize?client_id=2685278&scope=photos,wall,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&v=5.199

Или [vkhost.github.io](https://vkhost.github.io/) → **Kate Mobile** (не VK Admin) → Разрешить.

В адресной строке скопируйте от `access_token=` до `&`. Пришлите агенту:

`VK_USER_TOKEN=vk1.a....`

Заходите **своим профилем Марии**.

Запасные живые приложения на vkhost: Prisma, VFeed, «vk.com».

## Если ключ найдётся в старом чате

Ищите `VK_USER_TOKEN=` в https://cursor.com/agents/bc-01a04c79-162d-7499-9916-44bd41910a4f
Если это был VK Admin — скорее всего не сработает, берите Kate Mobile.

## Пока flood / нет ключа — фото с уже существующего поста

Скачать обложку: https://blog.mkekspert.ru/covers/vk-week2-vk.jpg  
Пост в сообществе с картинкой → ссылка `vk.com/photo-…` → агент делает новый пост.

```bash
python3 publish.py vk-from-post vk-week2 'https://vk.com/photo-222121025_…'
```

`publish_vk` при flood (error 9) или без `VK_USER_TOKEN` сам подставляет
уже залитое фото со стены (cache `/tmp/vk-last-wall-photo.txt` или
`VK_FALLBACK_PHOTO`) — пост не уходит текстом без картинки.
