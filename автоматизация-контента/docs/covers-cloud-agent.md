# Генерация обложек в Cloud Agent

## Главный путь (сейчас): Codex на ПК Марии

Cloud Agent **не** рисует боевые обложки сам (плагин Codex на VM недоступен).

1. Пост текстом + `covers_pipeline.py request <id>`
2. Codex в десктопном Cursor → файлы в `assets/covers/`
3. `covers_pipeline.py pickup --deploy`
4. VK: картинку крепит Мария вручную

→ Чеклист: [`checklists/covers-codex-pc.md`](../checklists/covers-codex-pc.md)

## Запасной путь в облаке: GenerateImage

Если Codex недоступен и Мария явно просит сгенерировать здесь:

1. Агент вызывает `GenerateImage` (`aspect_ratio=16:9` или `1:1` для VK).
2. Ресайз в репозиторий:
   - Дзен/TG: `assets/covers/{slug}.jpg` → **1200×630**
   - VK: `assets/covers/{slug}-vk.jpg` → **1080×1080**
3. `covers_pipeline.py pickup --deploy` или `dzen-rss setup`.

Не использовать PIL-fallback (цветной прямоугольник) для боевых обложек.

## Запасной путь (скрипт + OpenRouter)

Только если оба пути выше недоступны:

```env
# automation/.env  или Cloud Agent Secrets
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_IMAGE_MODEL=krea/krea-2-medium-turbo   # ~$0.015; muse требует 18+
```

```bash
python3 automation/generate_cover.py --slug my-post --title "..." --subtitle "..." --variant landscape --force
```

## Промпт-шаблон (стиль Telegram / brand-visual)

Один стиль для TG, VK и Дзен; отличается только размер.

Общее для всех:
- тёмный фон `#181818` / `#151515`
- полоса слева `#4EAF4E`, снизу `#FFCC4A`
- белый заголовок, жёлтый подзаголовок, зелёная строка `Мария Ковалева · mkekspert.ru`
- справа: абстрактный рост (столбики) и/или стрелка — по теме поста
- **без** claymorphism, пластилина, ivory 3D, терракотовых «катышков»

| Площадка | Размер | Файл |
|----------|--------|------|
| Дзен / TG | 1200×630 | `assets/covers/{slug}.jpg` |
| VK | 1080×1080 | `assets/covers/{slug}-vk.jpg` |

Референс: `assets/covers/tg-week5.jpg`.
Генерация: `automation/generate_cover.py` (`COVER_STYLE=mkekspert_dark`, `--no-gpt`).

## Правила экономии

- Сначала бриф в `briefs/covers/` (Codex) или согласование промпта.
- Одна платная генерация (OpenRouter) — только после ок.
- GenerateImage в облаке — только по явной просьбе.
