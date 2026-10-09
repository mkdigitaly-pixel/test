# AGENTS.md — автоматизация контента

Контент mkekspert: Дзен / TG / VK / блог.

## Пауза (с 2026-10-09)

Проект **остановлен**: не публиковать в TG/VK/Дзен/блог, не гонять `schedule run` на реал.  
Флаги: `AUTO_PUBLISH=false`, `DRY_RUN=true`, `VK_PUBLISH=off`.  
Снять паузу — только по явной просьбе Марии.

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
