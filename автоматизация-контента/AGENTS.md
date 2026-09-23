# AGENTS.md — автоматизация-контента (mkekspert)

Контент, SEO и HTML для Tilda/блога Марии Ковалевой.

## Карта

- README: `README.md`
- Каналы: `docs/content-channels.md`
- SEO-стек: `docs/seo-pipeline.md`, `checklists/seo-stack.md`, `seo/keywords.yaml`
- Tilda / Computer Use: `docs/tilda-computer-use.md`
- Главная HTML: `content/tilda-home.html` + `content/tilda-home.md`
- Разбор: `content/tilda-razbor-direct.html`
- Брендбук: ivory / terracotta `#A85A32` / emerald `#2A6F4C` / mustard `#D4AF37`; шрифты Unbounded + Manrope
- CTA формы на сайте: `#popup:cornerform-zapis-na-vstrechu`
- Превью блога: https://blog.mkekspert.ru/ (ветка `gh-pages`)

## Дзен / статьи

Перед правкой статей читай:

- `references/dzen-markup.md`, `references/dzen-prompt.md`
- `references/dzen-seo-rules.md`, `references/maria-voice.md`, `references/banned-phrases.md`
- Поиск тем: `references/topic-research.md`

Правила:

- В markdown только `[анкор](полный URL)` — никогда голый `mkekspert.ru/...` в тексте
- H1 только в YAML `title`/`h1`, не в теле
- Без эмодзи в H2; без копипаста с Promopult/Click/Habr
- HTML для Дзена: `cd automation && python3 publish.py format-dzen-html …`

## Tilda

Сайт остаётся на Tilda. Агент **не публикует** без явного «да».

Можно (если есть Browser/Computer Use): править блоки, тексты, Save.  
Нельзя без подтверждения: Publish, удаление страницы, DNS, SEO Site Settings, биллинг.

Если Computer Use нет — отдай HTML для ручной вставки (T123), не имитируй правку редактора.

Идентификаторы: project `9707577`; разбор page `146521496` / alias `razbor-direct`.

## SEO / blog

```bash
cd automation
python3 seo_pipeline.py audit
python3 seo_pipeline.py status
python3 seo_pipeline.py report
```

Деплой статики блога — ветка `gh-pages` (корень: `home-preview.html`, `home-assets/`, …).  
Исходники превью часто в `articles/dzen/blog-site/`.

## Секреты

Шаблон доступов: `ДОСТУПЫ.env` (в gitignore). Не коммитить и не цитировать значения ключей.
