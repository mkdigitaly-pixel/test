# SEO-пайплайн mkekspert (органика Яндекс)

Цель: статьи и посадочные растут в **органической выдаче Яндекса** → трафик на `blog.mkekspert.ru` и заявки на `mkekspert.ru/razbor-direct`.

Дзен / TG / VK — отдельный контур дистрибуции. Этот документ — **поисковый стек**.

---

## Стек (что за что отвечает)

| Слой | Где | Зачем |
|------|-----|--------|
| Коммерческий сайт | `https://mkekspert.ru` (Tilda) | услуги, разбор, доверие |
| SEO-статьи | `https://blog.mkekspert.ru` (GitHub Pages) | информационные / кейс-запросы |
| Индекс и ошибки | Яндекс.Вебмастер (оба хоста) | sitemap, переобход, запросы |
| Поведение | Яндекс.Метрика `97606312` | цели, пути, отказы |
| Ключи и план | `seo/keywords.yaml` + `plan/` | что писать |
| Бриф → статья | `briefs/` → `articles/dzen/` | контент |
| Публикация | `publish.py` + RSS | blog + Дзен |
| Позиции | `seo/positions/` + `seo_pipeline.py` | съём и отчёт |
| Чеклисты | `checklists/seo-stack.md` | разовые настройки |

```
ключи / SERP-гэп
      ↓
бриф (templates/brief.md)
      ↓
статья + uniqueness check
      ↓
publish → blog.mkekspert.ru (+ Дзен по желанию)
      ↓
Вебмастер: переобход URL
      ↓
съём позиций (раз в неделю)
      ↓
отчёт → правки / новые темы
```

---

## Этапы пайплайна (статусы ключа)

| Статус | Смысл |
|--------|--------|
| `idea` | тема есть, бриф нет |
| `brief` | бриф готов |
| `draft` | статья в репо |
| `published` | URL на blog живой |
| `indexed` | в индексе (по Вебмастеру) |
| `tracking` | ключ в мониторе позиций |
| `top10` / `top3` | цель достигнута |
| `refresh` | нужно обновить текст |

Агент ведёт статусы в `seo/keywords.yaml`. Публикация по-прежнему через `queue/publish-queue.yaml`.

---

## Команды

```bash
cd автоматизация-контента/automation

# Живой аудит готовности (Tilda + blog)
python3 seo_pipeline.py audit

# Банк ключей
python3 seo_pipeline.py keywords list
python3 seo_pipeline.py keywords add --query "почему нет заявок яндекс директ" --url https://blog.mkekspert.ru/articles/no-leads-direct.html --pillar P1

# Записать позиции вручную (из выдачи / Вебмастера)
python3 seo_pipeline.py positions record --query "почему нет заявок яндекс директ" --pos 14 --engine yandex

# Снимок из YAML-файла замеров
python3 seo_pipeline.py positions import seo/../seo/positions/manual-input.example.yaml

# Недельный отчёт
python3 seo_pipeline.py report

# Статус воронки контента×SEO
python3 seo_pipeline.py status
```

Опционально (если есть ключ XMLRiver / аналог в `.env`):

```
SEO_SERP_PROVIDER=xmlriver
SEO_SERP_USER=
SEO_SERP_KEY=
```

```bash
python3 seo_pipeline.py positions fetch   # автосъём по банку ключей
```

Без ключа автосъём пропускается — позиции только вручную / импорт.

---

## Что обязательно до масштабирования статей

См. [`checklists/seo-stack.md`](../checklists/seo-stack.md):

1. Ссылка с Tilda → `blog.mkekspert.ru`
2. `blog.mkekspert.ru` в Вебмастере + sitemap
3. Sitemap основного сайта на **https**
4. Редирект `www` → без www (или наоборот — один канонический хост)

Без пункта 1–2 статьи пишутся «в вакуум»: поиск слабо связывает блог с брендом.

---

## Связь с контент-планом

- Кластеры P1–P4: [`plan/dzen-seo-content-plan.md`](../plan/dzen-seo-content-plan.md)
- Темы из конкурентов: [`references/topic-research.md`](../references/topic-research.md)
- Правила статьи: [`references/dzen-seo-rules.md`](../references/dzen-seo-rules.md)
- Бренд в выдаче: [`checklists/brand-organic-serp.md`](../checklists/brand-organic-serp.md)
