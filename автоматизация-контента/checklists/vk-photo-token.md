# VK: картинка к посту

Ключ сообщества публикует текст, но **не загружает новое фото**. Уже лежащее
на стене фото он прикрепить умеет.

Приложение VK ID: **54768786** (не 54768817 — этот id был ошибочный).

## Новый пост с фото без OAuth

1. Откройте VK **своим профилем Марии**.
2. Скачайте обложку: https://blog.mkekspert.ru/covers/vk-week2-vk.jpg
3. В `klientyandtrafik` создайте запись **от имени сообщества** только с этой картинкой.
4. Фото → «Скопировать ссылку» (`https://vk.com/photo-222121025_…`) — пришлите агенту.

```bash
cd automation
python3 publish.py vk-from-post vk-week2 'https://vk.com/photo-222121025_…'
```

## Если входим по ссылке VK (клиент 54768786)

В кабинете приложения 54768786 добавьте redirect:

`https://blog.mkekspert.ru/vk-oauth.html`

Затем откройте **своим профилем**:

https://oauth.vk.com/authorize?client_id=54768786&display=page&redirect_uri=https://blog.mkekspert.ru/vk-oauth.html&scope=photos,groups,offline&response_type=token&v=5.199

Ключ `vk1.a.…` пришлите сообщением `VK_USER_TOKEN=...`.

