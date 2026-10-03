# AGENTS.md — автоматизация контента

Контент mkekspert: Дзен / TG / VK / блог.

## Обложки (по умолчанию)

1. Cloud Agent генерирует обложки через **GenerateImage** → `assets/covers/`.
2. Публикует текст (VK без фото: `VK_PHOTOS=manual`).
3. VK-картинку Мария крепит вручную с `blog.mkekspert.ru/covers/{slug}-vk.jpg`.

Codex на ПК — опционально (брифы в `briefs/covers/`).

Чеклист: `checklists/covers-codex-pc.md`.

## Не делать

- Не коммить `.env` / `ДОСТУПЫ.env`.
- Не вызывать VK photo upload / flood-пробы.
- Не Publish в Tilda без явного «да».
