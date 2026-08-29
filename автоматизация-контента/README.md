# Автоматизация контента mkekspert

SEO-статьи, кейсы и нарезки для [mkekspert.ru](https://mkekspert.ru), [Дзен](https://dzen.ru/klientyandtrafik), [Telegram](https://t.me/mariyaprodirect).

## Структура

```
автоматизация-контента/
├── briefs/           # брифы перед написанием
├── articles/
│   ├── dzen/         # статьи для Дзена
│   └── tg/           # посты для канала
├── references/
│   ├── brand.md      # бренд, ссылки, CTA, цифры кейсов
│   └── utm.md        # UTM-метки
└── templates/        # шаблоны статьи и брифа
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
3. Согласование с Марией
4. Публикация (Tilda / Дзен / TG — вручную или через автоматизацию позже)

## Опционально позже

- Яндекс Wordstat MCP — реальные частоты
- publish-mcp — автопостинг в Telegram
- dzen skill — автопубликация в Дзен
