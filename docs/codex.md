# Codex в этом репозитории

OpenAI Codex (расширение в Cursor / CLI) подхватывает инструкции из **`AGENTS.md`**.

## Файлы

| Путь | Зона |
|------|------|
| [`AGENTS.md`](../AGENTS.md) | Корень репо |
| [`автоматизация-контента/AGENTS.md`](../автоматизация-контента/AGENTS.md) | Контент / Tilda / SEO |
| [`parser/AGENTS.md`](../parser/AGENTS.md) | Парсеры |

Чем ближе файл к рабочей папке — тем выше приоритет (Codex склеивает цепочку сверху вниз).

## Как пользоваться в Cursor

1. Установить расширение **Codex**.
2. Открыть этот репозиторий.
3. Command Palette → **New Codex Agent** (или панель Codex).
4. Работать из нужной папки (`автоматизация-контента` или `parser`), чтобы подтянулся вложенный `AGENTS.md`.

Проверка (если установлен CLI):

```bash
codex --ask-for-approval never "Summarize the current instructions."
```

## Cursor rules vs AGENTS.md

| | Cursor | Codex |
|--|--------|-------|
| Правила | `.cursor/rules/*.mdc` | `AGENTS.md` |
| Skills | `.cursor/skills/` | опционально `.agents/skills/` |

Правила Cursor для парсеров и контента **остаются**. `AGENTS.md` — краткий слой для Codex, без копирования всех `.mdc` целиком.
