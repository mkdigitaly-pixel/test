# VK: картинка к посту

Ключ сообщества публикует текст, но **не загружает новое фото**.

## Пауза до 2026-10-19 (flood)

После error 9 на аккаунте: **месяц не трогаем** `VK_USER_TOKEN` /
`photos.getWallUploadServer` / recycle-фото.

- В коде: `VK_TEXT_ONLY_UNTIL=2026-10-19` (по умолчанию).
- Все VK-посты идут **только текстом**.
- Команды `vk-attach-cover` / `vk-from-post` и `vk_cover_retry.py` —
  отказ до этой даты.
- Снять паузу раньше: `VK_TEXT_ONLY_UNTIL=0` в `.env` (только когда
  Мария явно попросит проверить flood одним запросом).

## Получить ключ (после паузы)

Не 54768786 — у него Security Error. Берём **Kate Mobile**:

https://oauth.vk.com/authorize?client_id=2685278&scope=photos,wall,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&v=5.199

Или [vkhost.github.io](https://vkhost.github.io/) → **Kate Mobile** → Разрешить.

В адресной строке: от `access_token=` до `&` → `VK_USER_TOKEN=vk1.a....`
Профиль Марии.

## После паузы — обложка к посту

```bash
python3 publish.py vk-attach-cover no-leads-direct --post-id 220
```

Или новый пост с уже залитым фото (не при flood-паузе):

```bash
python3 publish.py vk-from-post vk-week2 'https://vk.com/photo-222121025_…'
```
