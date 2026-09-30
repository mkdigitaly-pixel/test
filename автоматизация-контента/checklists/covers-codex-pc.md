# Обложки: Cloud Agent делает сам

## Схема (по умолчанию)

1. **Облако** публикует текст и генерирует обложки через **GenerateImage**.
2. Файлы сразу в `assets/covers/` (+ при необходимости `pickup --deploy` на blog).
3. **VK:** Мария крепит картинку вручную к посту (`VK_PHOTOS=manual`).

Codex на ПК **не обязателен**. Брифы в `briefs/covers/` — запасной путь, если хотите рисовать в Codex сами.

## Размеры

| Файл | Размер | Куда |
|------|--------|------|
| `assets/covers/{slug}.jpg` | 1200×630 | Дзен / TG |
| `assets/covers/{slug}-vk.jpg` | 1080×1080 | VK вручную |

## Команды

```bash
python3 covers_pipeline.py status
python3 covers_pipeline.py pickup --deploy
```

## Стиль

Claymorphism, ivory `#FDFBF7`, терракота / изумруд / золото.
Подробности: `docs/covers-cloud-agent.md`.
