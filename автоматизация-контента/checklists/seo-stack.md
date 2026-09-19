# SEO-стек — разовые настройки (mkekspert)

Сайты: `https://mkekspert.ru` + `https://blog.mkekspert.ru`  
Документ пайплайна: [`docs/seo-pipeline.md`](../docs/seo-pipeline.md)  
Проверка с сервера: `python3 automation/seo_pipeline.py audit`

Отмечайте: `[ ]` → `[x]`

---

## A. Связка сайта и блога (критично)

- [ ] В подвале Tilda в блоке «Блог и кейсы» есть ссылка **Блог** → https://blog.mkekspert.ru  
  Текст: [`content/tilda-footer-social.md`](../content/tilda-footer-social.md)
- [ ] На главной / в меню есть путь к статьям (не только Дзен)
- [ ] `audit` не пишет `FAIL: no blog.mkekspert.ru link on main`

---

## B. Вебмастер

- [ ] Добавлен `https://mkekspert.ru`, права подтверждены
- [ ] Добавлен **`https://blog.mkekspert.ru`**, права подтверждены
- [ ] Sitemap основного: `https://mkekspert.ru/sitemap.xml` (именно https)
- [ ] Sitemap блога: `https://blog.mkekspert.ru/sitemap.xml`
- [ ] Переобход: главная, razbor-direct, главная блога, 3 свежие статьи
- [ ] Регион / Яндекс Бизнес — по [`brand-organic-serp.md`](brand-organic-serp.md)

---

## C. Техника Tilda

- [ ] Sitemap отдаёт URL с **https://** (не http://) — переопубликовать сайт при необходимости
- [ ] Редирект: `www.mkekspert.ru` → `mkekspert.ru` (или наоборот, но один каноник)
- [ ] `robots.txt` указывает Sitemap на https
- [ ] Favicon и имя **МК Эксперт** на основном сайте (как на blog)

---

## D. Метрика

- [ ] Счётчик на Tilda и на blog (один id)
- [ ] Цель: отправка формы разбора / заявка
- [ ] В отчётах смотреть `utm_source=blog` и `utm_source=dzen`

---

## E. Контент × SEO (еженедельно)

- [ ] Новые темы → `seo/keywords.yaml` со статусом `idea`
- [ ] Бриф → статья → publish
- [ ] После публикации: статус ключа `published`, URL проставлен
- [ ] Раз в неделю: замер позиций → `seo/positions/YYYY-MM-DD.yaml` → `seo_pipeline.py report`
- [ ] Топ-11…30 — в очередь на усиление (объём, FAQ, внутренние ссылки)

---

## F. Опционально: автосъём SERP

- [ ] Ключ XMLRiver (или аналог) в `automation/.env`
- [ ] `SEO_SERP_PROVIDER=xmlriver` + `SEO_SERP_USER` / `SEO_SERP_KEY`
- [ ] `python3 seo_pipeline.py positions fetch`

Без ключа — ручной импорт из example YAML.
