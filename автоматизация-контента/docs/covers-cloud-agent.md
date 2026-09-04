# Генерация обложек в Cloud Agent

## Главный путь (без OpenRouter, как на ПК)

В Cursor Cloud Agent есть встроенный инструмент **GenerateImage** — тот же, что на десктопе.

1. Агент вызывает `GenerateImage` с промптом + `aspect_ratio=16:9` (+ опционально reference).
2. Файл появляется в `/opt/cursor/artifacts/assets/`.
3. Копируем/ресайзим в `assets/covers/{slug}.jpg` (1200×630).
4. Деплой: `python3 -c "from automation.dzen_rss import deploy_gh_pages; deploy_gh_pages()"`.

**OpenRouter не нужен** для этого пути. Кредиты OpenRouter не тратятся.

## Запасной путь (скрипт + OpenRouter)

Только если встроенная генерация недоступна:

```env
# automation/.env  или Cloud Agent Secrets
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_IMAGE_MODEL=krea/krea-2-medium-turbo   # ~$0.015; muse требует 18+
```

```bash
python3 automation/generate_cover.py --slug my-post --title "..." --subtitle "..." --variant landscape --force
```

## Промпт-шаблон (claymorphism / Дзен)

См. актуальный текст в `automation/generate_cover.py` → `openrouter_prompt()`  
и референс: `assets/covers/_import/style-ref.png`.

## Правила экономии

- Сначала согласовать промпт/референс.
- Одна платная генерация (OpenRouter) — только после ок.
- Для итераций стиля — GenerateImage (встроенный).
