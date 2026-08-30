# Автоматизация контента mkekspert

SEO-статьи, кейсы и нарезки для [mkekspert.ru](https://mkekspert.ru), [Дзен](https://dzen.ru/klientyandtrafik), [Telegram](https://t.me/mariyaprodirect).

## Структура

```
автоматизация-контента/
├── automation/       # скрипт публикации TG → Дзен, VK
├── queue/            # очередь draft → approved → published
├── briefs/           # брифы перед написанием
├── articles/
│   ├── dzen/         # статьи для Дзена
│   └── tg/           # посты для канала
├── references/
│   ├── brand.md              # бренд, ссылки, CTA, цифры кейсов
│   ├── banned-phrases.md     # запрещённые нейроштампы (AI-клише)
│   ├── program-prompts.md    # программа 3 дней (профайлинг, закреп, сторителлинг)
│   └── utm.md                # UTM-метки
├── prompts/                  # промпты по дням программы
│   ├── day2-pinned-post.md
│   └── day3-storytelling.md
└── templates/                # шаблоны статьи и брифа
```

## Правила для агента (Cursor)

| Файл | Назначение |
|------|------------|
| `parser/.cursor/rules/mkekspert-seo-content.mdc` | SEO: структура, мета, чеклист |
| `parser/.cursor/rules/mkekspert-dzen.mdc` | Формат статей Дзен + нарезка TG |
| `parser/.cursor/skills/write-seo-article-mkekspert/` | Skill: алгоритм написания |

Правила подхватываются автоматически при работе в папке `автоматизация-контента/`.

## Workflow

1. Бриф → `briefs/`
2. Статья → `articles/dzen/`
3. Согласование с Марией (`queue approve`)
4. Публикация → `automation/publish.py` (TG → Дзен через @zen_sync_bot)

Подробно: [`automation/README.md`](automation/README.md)

## Опционально позже

- Яндекс Wordstat MCP — реальные частоты
- publish-mcp — автопостинг из Cursor без скрипта
- Обложки по шаблону (генерация картинок для Дзена)
