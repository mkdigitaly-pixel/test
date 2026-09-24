# VK: картинки к посту

## Режим: вручную (по умолчанию)

`VK_PHOTOS=manual` — скрипт публикует **только текст**.
Картинки Мария прикрепляет сама в VK к уже вышедшему посту.

Пайплайн обложек (Codex на ПК): `checklists/covers-codex-pc.md`.

Готовые файлы обложек:
- локально: `assets/covers/{id}-vk.jpg` (1080×1080)
- на сайте: `https://blog.mkekspert.ru/covers/{id}-vk.jpg`

Пример: после поста `vk-week3` открыть стену → изменить → прикрепить
`https://blog.mkekspert.ru/covers/vk-week3-vk.jpg` (если файл есть).

Не вызываем `VK_USER_TOKEN` / `photos.getWallUploadServer` / recycle.

## Вернуть автозагрузку (только по явной просьбе)

В `.env`:

```
VK_PHOTOS=auto
```

Нужен живой `VK_USER_TOKEN` (Kate Mobile), без flood на аккаунте.
См. oauth ниже. Одну проверку — не в цикле.

```bash
python3 publish.py vk-attach-cover 220 no-leads-direct
```

## Получить VK_USER_TOKEN (если снова понадобится API)

Kate Mobile:

https://oauth.vk.com/authorize?client_id=2685278&scope=photos,wall,groups,offline&redirect_uri=https://oauth.vk.com/blank.html&display=page&response_type=token&v=5.199

Или [vkhost.github.io](https://vkhost.github.io/) → **Kate Mobile** → Разрешить.
Профиль Марии. В URL: от `access_token=` до `&`.
