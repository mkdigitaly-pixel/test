# VK: картинка к посту

Ключ сообщества (`VK_ACCESS_TOKEN`) публикует **текст**. Обложку он **не загружает**:
`photos.getWallUploadServer` → error 27. Фото из сообщений (`saveMessagesPhoto`)
`wall.post` принимает, но на стене **не показывает**.

Нужен пользовательский ключ `VK_USER_TOKEN` (`vk1.a.…`, не `vk2.a.…` и не ключ сообщества).
Им загружаем фото, постом по-прежнему идёт ключ сообщества.

Приложение vkhost / Kate Mobile VK блокирует. Берём ключ через своё приложение.

## Что нужно в `.env`

```
VK_ACCESS_TOKEN=ключ сообщества (стена)
VK_GROUP_ID=222121025
VK_USER_TOKEN=пользовательский ключ (фото + offline)
```

## Как получить `VK_USER_TOKEN` (один раз)

Уже есть приложение VK ID **54768817**.

1. В кабинете приложения: [id.vk.com/about/business](https://id.vk.com/about/business)
   добавьте доверенный redirect URI:

   `https://blog.mkekspert.ru/vk-oauth.html`

2. Откройте ссылку **под своим аккаунтом** (админ `klientyandtrafik`):

   https://oauth.vk.com/authorize?client_id=54768817&display=page&redirect_uri=https://blog.mkekspert.ru/vk-oauth.html&scope=photos,groups,offline&response_type=token&v=5.199

3. Разрешите доступ. Откроется страница блога с ключом `vk1.a.…`.
   Пришлите его агенту сообщением `VK_USER_TOKEN=...` (в git не коммитить).

Если будет **Security Error** — в настройках приложения тип должен быть
Standalone / «Другое», не только Web, и redirect URI — символ в символ как выше.
Не открывайте `oauth.vk.com/blank.html`: для Web-приложения он как раз даёт Security Error.

После записи ключа в `.env` обложку к уже вышедшему посту:

```bash
cd automation
python3 publish.py vk-attach-cover 206 vk-week2
```

Новые посты подхватят обложку сами.

## Проверка

```bash
cd automation
python3 publish.py publish vk-post vk-week2 --dry-run
```

С токеном: `(текст+фото)`. Без токена: предупреждение и `(текст)`.
