# AGENTS.md — автоматизация контента

Контент mkekspert: Дзен / TG / VK / блог.

## Обложки (обязательный пайплайн)

1. Cloud Agent публикует **текст** (VK без картинки: `VK_PHOTOS=manual`).
2. `python3 automation/covers_pipeline.py request <id>` → бриф в `briefs/covers/`.
3. **Codex на ПК Марии** рисует JPG по брифу в `assets/covers/`.
4. Cloud: `python3 automation/covers_pipeline.py pickup --deploy`.
5. VK-картинку Мария крепит вручную.

Чеклист: `checklists/covers-codex-pc.md`.

## Не делать

- Не коммить `.env` / `ДОСТУПЫ.env`.
- Не вызывать VK photo upload / flood-пробы.
- Не Publish в Tilda без явного «да».
