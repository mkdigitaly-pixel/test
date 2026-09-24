# Обложки: Cloud Agent ↔ Codex (ПК)

## Схема

1. **Облако** публикует текст (VK без фото, TG/Dzen по расписанию) и ставит задачу:
   ```bash
   cd автоматизация-контента/automation
   python3 covers_pipeline.py request <id> [--vk-post-id N]
   ```
2. Появляется бриф: `briefs/covers/{slug}.md`
3. **Codex на ПК** (расширение в Cursor) открывает бриф → сохраняет JPG в `assets/covers/`
4. Пуш в ту же ветку **или** фраза агенту: `covers pickup`
5. Облако:
   ```bash
   python3 covers_pipeline.py pickup --deploy
   ```
   - помечает `ready` в `queue/covers-inbox.yaml`
   - выкладывает на `https://blog.mkekspert.ru/covers/…`
6. **VK:** Мария крепит картинку вручную (`VK_PHOTOS=manual`).

## Размеры

| Файл | Размер | Куда |
|------|--------|------|
| `assets/covers/{slug}.jpg` | 1200×630 | Дзен / TG |
| `assets/covers/{slug}-vk.jpg` | 1080×1080 | VK вручную |

## Команды

```bash
python3 covers_pipeline.py request vk-week3 --vk-post-id 221
python3 covers_pipeline.py status
python3 covers_pipeline.py pickup --deploy
```

## Стиль

Claymorphism, ivory `#FDFBF7`, терракота / изумруд / золото.
Референс: `assets/covers/_import/style-ref.png`.
Центральный 3D-объект **разный** у каждого поста.
Подробности: `docs/covers-cloud-agent.md`, `brandbook/covers.md`.

## Что не делать

- Не долбить `VK_USER_TOKEN` / upload фото через API.
- Не подставлять recycle-фото со стены.
- Не оставлять PIL-заглушки как боевые обложки.
