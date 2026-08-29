---
name: write-seo-article-mkekspert
description: >-
  Пишет SEO-статьи, брифы и кейсы для mkekspert.ru и Дзена (klientyandtrafik):
  семантика, структура под Яндекс, версии для Tilda/Дзен/TG. Триггеры: SEO-статья,
  написать статью для Дзена, кейс для mkekspert, контент для klientyandtrafik.
---

# Написание SEO-статьи mkekspert

## Когда применять
- Запрос на SEO-статью, кейс, гайд по Яндекс Директу
- Контент для Дзена, Tilda, нарезка для Telegram

## Обязательно прочитать
1. `parser/.cursor/rules/mkekspert-seo-content.mdc`
2. Для Дзена: `parser/.cursor/rules/mkekspert-dzen.mdc`
3. `автоматизация-контента/references/brand.md`
4. `автоматизация-контента/references/utm.md`
5. Шаблон: `автоматизация-контента/templates/article-dzen.md`

## Алгоритм

### 1. Бриф
- Ключ + LSI через анализ выдачи и Wordstat (если доступен)
- Файл: `автоматизация-контента/briefs/YYYY-MM-DD-slug.md`
- Поля: интент, ЦА, гэпы конкурентов, объём, CTA, utm_campaign

### 2. Черновик
- `автоматизация-контента/articles/dzen/YYYY-MM-DD-slug.md` (или `articles/ready-…`)
- Мета-блок YAML в начале
- Структура по правилам dzen или seo-content

### 3. Проверка
- Чеклист из mkekspert-seo-content.mdc
- CTA + UTM из brand.md
- Цифры только из подтверждённых кейсов (brand.md или исходник VC/клиент)

### 4. Нарезка (если просят)
- `articles/tg/YYYY-MM-DD-slug-post.md` — 1–2 поста для mariyaprodirect

## Выход
Краткий отчёт: путь к файлам, title, ключ, CTA-ссылка.
