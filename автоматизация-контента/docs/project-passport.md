# Паспорт проекта mkekspert (контент-автоматизация)

Куда что лежит и как зайти. **Секреты (токены) сюда не пишем** — только имена переменных и где они хранятся.

Обновлено: 2026-10-09.

---

## 1. Зачем проект

Автоматизация контента **МК Эксперт** (Мария Ковалева): длинные статьи → блог + RSS → Дзен; тизеры и свои посты → Telegram / VK; обложки на GitHub Pages.

Три публичные «витрины»:

| Витрина | URL | Кто правит |
|---------|-----|------------|
| Сайт | https://mkekspert.ru | Tilda |
| Блог статей | https://blog.mkekspert.ru | этот репо → ветка `gh-pages` |
| Соцсети | Дзен / TG / VK | `publish.py` + очереди |

---

## 2. Репозиторий и код

| Что | Значение |
|-----|----------|
| GitHub | https://github.com/mkdigitaly-pixel/test |
| SSH remote | `git@github.com:mkdigitaly-pixel/test.git` |
| Папка проекта в репо | `автоматизация-контента/` |
| Рабочая ветка контента | `cursor/schedule-catchup-8631` |
| Стиль блога (Onest) | `cursor/blog-onest-style-8631` → PR #12 |
| Базовая ветка для PR | `cursor/rename-test-to-work-e9d0` |
| PR расписания / контента | https://github.com/mkdigitaly-pixel/test/pull/8 |
| PR стиля блога | https://github.com/mkdigitaly-pixel/test/pull/12 |

### Как открыть код у себя

1. GitHub → репозиторий `mkdigitaly-pixel/test`
2. Или на ПК: `git clone git@github.com:mkdigitaly-pixel/test.git`
3. Папка: `test/автоматизация-контента/`

---

## 3. Cloud Agent (Cursor)

| Что | Значение |
|-----|----------|
| Чат агента | https://cursor.com/agents/bc-95eaf9e4-d3bb-4ef3-9ef2-76fc8a2a8631 |
| Аккаунт владельца | mkdigitaly@gmail.com (Мария Ковалева) |
| Режим | Self-hosted / private worker |
| Таймер расписания | `schedule-run-daily` — cron `5 7,9,11 * * *` (UTC) → **10:05 / 12:05 / 14:05 МСК** |

Агент сам запускает `python3 publish.py schedule run` по таймеру.

---

## 4. Сайты и каналы (публичные ссылки)

| Куда | URL |
|------|-----|
| Сайт (Tilda) | https://mkekspert.ru |
| Разбор Директа | https://mkekspert.ru/razbor-direct |
| Блог статей | https://blog.mkekspert.ru |
| RSS для Дзена | https://blog.mkekspert.ru/dzen-feed.xml |
| Обложки | https://blog.mkekspert.ru/covers/{slug}.jpg и `{slug}-vk.jpg` |
| Дзен-канал | https://dzen.ru/klientyandtrafik |
| Telegram основной | https://t.me/mariyaprodirect (`@mariyaprodirect`) |
| Telegram Дзен-sync | `@dzenkovaleva` (статьи → @zen_sync_bot) |
| VK группа | https://vk.com/klientyandtrafik (id `222121025`) |
| Личка Марии | `@Mariya1740` |

### Где правится хостинг блога

| Что | Где |
|-----|-----|
| GitHub Pages | ветка `gh-pages` репо `mkdigitaly-pixel/test` |
| Домен | `blog.mkekspert.ru` → CNAME на GitHub Pages |
| Деплой | `publish.py` / `dzen_rss.deploy_gh_pages()` после статей |
| Шаблон HTML/CSS | `automation/dzen_rss.py` (`BLOG_CSS`, `BLOG_FONTS`, `_site_chrome`) |

Основной сайт **mkekspert.ru** — Tilda (не этот блог).

### Стиль блога (актуально)

| Элемент | Как |
|---------|-----|
| Шрифт | **Onest** (Google Fonts): текст 400, меню/кнопки 500–600, заголовки 700–800 |
| Фон | ivory `#FDFBF7` (brandbook) |
| Акцент / кнопки | терракота `#A85A32` |
| Текст | графит `#3D3D3D` |
| Карточки | белые, скругление, лёгкая тень, hover |

Палитра-источник: `brandbook/tokens.json`, `brandbook/colors.md`.

---

## 5. Где лежат файлы (структура)

Корень: `автоматизация-контента/`

```
автоматизация-контента/
├── articles/
│   ├── dzen/articles/     # полные статьи → RSS / Дзен
│   ├── dzen/teasers/tg/   # тизеры → @mariyaprodirect
│   ├── dzen/teasers/vk/   # тизеры → VK (сейчас на паузе)
│   ├── dzen/html/         # HTML-экспорт статей
│   ├── dzen/feed.xml      # локальная RSS-лента
│   ├── dzen/blog-site/    # favicon, zen_*.html, home-assets → gh-pages
│   ├── tg/                # свои посты Telegram
│   └── vk/                # свои посты VK
├── assets/covers/         # обложки JPG (16:9 и *-vk 1:1)
├── automation/            # publish.py, dzen_rss.py, generate_cover.py, .env
├── queue/
│   ├── publish-queue.yaml     # кампании Дзен
│   ├── posts-queue.yaml       # посты TG/VK
│   ├── posting-schedule.yaml  # расписание слотов
│   └── covers-inbox.yaml      # очередь обложек
├── briefs/covers/         # брифы на обложки
├── docs/                  # инструкции (этот файл здесь)
├── checklists/            # чеклисты настройки
├── references/            # голос, разметка, бренд
├── plan/                  # контент-план, расписание
├── brandbook/             # цвета / токены
├── content/               # черновики Tilda-home и др.
├── .env                   # флаги (например VK_PUBLISH) — не коммитить
├── automation/.env        # токены — не коммитить
└── ДОСТУПЫ.env            # Tilda / Webmaster — не коммитить
```

---

## 6. Секреты и доступы (где лежат, что означают)

**Не коммитить:** `.env`, `automation/.env`, `ДОСТУПЫ.env`.

| Файл | Что внутри (имена ключей) |
|------|---------------------------|
| `automation/.env` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MAIN_CHANNEL_ID`, `TELEGRAM_DZEN_CHANNEL_ID`, `VK_ACCESS_TOKEN`, `VK_USER_TOKEN`, `VK_GROUP_ID`, `VK_PHOTOS`, `VK_PUBLISH`, `AUTO_PUBLISH`, `DZEN_*`, Tilda-ключи (если скопированы) |
| `.env` (корень папки) | `VK_PUBLISH` (флаг паузы VK; перекрывает automation/.env) |
| `ДОСТУПЫ.env` | `TILDA_*`, `WEBMASTER_YANDEX_VERIFICATION` |
| Образец без секретов | `automation/.env.example` |

### Важные флаги сейчас (2026-10-09)

| Флаг | Значение | Смысл |
|------|----------|--------|
| `AUTO_PUBLISH` | `true` | Расписание публикует по-настоящему |
| `VK_PHOTOS` | `manual` | В VK только текст; картинки крепит Мария |
| `VK_PUBLISH` | `off` | **Новые посты/тизеры VK не публикуются** (слоты ждут) |
| `DZEN_PUBLISH_MODE` | `auto` | Длинные статьи → RSS, короткие → zen_sync |
| `DZEN_RSS_DEPLOY_GH_PAGES` | `true` | После статьи — деплой на blog |
| `DZEN_RSS_DRAFT` | `false` | В RSS без native-draft |
| `DZEN_TG_NOTIFY` | `false` | Без доп. TG-уведомлений о RSS |

Чтобы снова публиковать VK: в `automation/.env` (и корневой `.env`) поставить `VK_PUBLISH=on` и написать агенту.

---

## 7. Как зайти в кабинеты

| Сервис | Как зайти |
|--------|-----------|
| GitHub | github.com под аккаунтом с доступом к `mkdigitaly-pixel/test` |
| Cursor Cloud Agent | https://cursor.com → Agents → чат выше |
| Дзен Студия | https://dzen.ru/studio → канал «Клиенты и трафик» / klientyandtrafik |
| Telegram | приложение / web → `@mariyaprodirect`, `@dzenkovaleva` |
| VK | vk.com → сообщество klientyandtrafik (админ-права) |
| Tilda | tilda.cc → проект mkekspert (ключи в `ДОСТУПЫ.env`) |
| Яндекс.Метрика | счётчик блога/сайта `97606312` |
| Яндекс.Вебмастер | verification в `ДОСТУПЫ.env` / мета на blog |

Логина/пароля Студии Дзена в `.env` **нет** — публикация статей через RSS (`dzen-feed.xml`).

---

## 8. Как публикуется (поток)

Ритм (`queue/posting-schedule.yaml`, timezone `Europe/Moscow`):

```
вт/чт 10:00  publish_dzen     → HTML + feed.xml → blog.mkekspert.ru → Дзен забирает RSS
вт/чт 12:00  publish_teasers  → TG тизер (+ VK тизер, если VK_PUBLISH=on)
ср     11:00  publish_tg_post  → @mariyaprodirect
пт     11:00  publish_vk_post  → VK (сейчас на паузе)
ср/пт  15:00  vc_manual        → VC.ru вручную (опционально)
```

Таймер агента бьёт в 10:05 / 12:05 / 14:05 МСК и догоняет просроченные слоты.

Команды вручную:

```bash
cd автоматизация-контента/automation
python3 publish.py schedule run
python3 publish.py schedule list
python3 publish.py publish dzen <id>
python3 publish.py publish teasers <id>
python3 publish.py publish tg-post <id>
# VK сейчас: не вызывать, пока VK_PUBLISH=off
```

Очереди: `queue/publish-queue.yaml`, `queue/posts-queue.yaml`, `queue/posting-schedule.yaml`.

### Статус кампаний Дзен (снимок)

| Статус | id |
|--------|-----|
| published | `7-errors-direct`, `penoplast-case`, `no-leads-direct`, `autotarget-b2b`, `metrika-goals`, `epk-leads`, `rsa-vs-search`, `budget-waste`, `choose-directologist` |
| approved (в расписании) | `audit-direct`, `landing-conversion`, `negative-keywords` |
| draft | `chp-upp-case`, `offline-conversions`, `search-retargeting` |

### Ближайшие слоты (ориентир)

| Дата | Действие | id |
|------|----------|-----|
| 2026-10-09 | dzen + teasers | `audit-direct` |
| 2026-10-10 | vk-post | `vk-week6` (ждёт `VK_PUBLISH=on`) |
| 2026-10-14 | dzen + teasers | `direct-price` |
| 2026-10-15 | tg-post | `tg-week7` |
| 2026-10-16 | dzen + teasers | `landing-conversion` |

Актуальный список: `python3 publish.py schedule list`.

---

## 9. Обложки

| Размер | Файл | Куда |
|--------|------|------|
| 1200×630 | `assets/covers/{slug}.jpg` | Дзен / TG / блог |
| 1080×1080 | `assets/covers/{slug}-vk.jpg` | VK вручную |

Стиль: тёмный бренд как в Telegram (`references/brand-visual.md`, `generate_cover.py`) — **без пластилина / claymorphism**.  
Готовые URL: `https://blog.mkekspert.ru/covers/{slug}.jpg` и `{slug}-vk.jpg`.

Генерация: Cloud Agent (GenerateImage) → `assets/covers/`; fallback PIL в `generate_cover.py`.  
Чеклисты: `docs/covers-cloud-agent.md`, `checklists/covers-codex-pc.md`.

---

## 10. Что сказать агенту (шпаргалка)

| Нужно | Фраза |
|-------|--------|
| Запустить расписание | «запусти schedule run» |
| Статус очереди | «что по расписанию?» |
| Снова публиковать VK | «включи VK_PUBLISH=on» |
| Не трогать VK | уже `VK_PUBLISH=off` |
| Картинка к VK-посту | «ссылку на обложку для поста #N» |
| Статья в блог/RSS | «опубликуй dzen &lt;id&gt;» |
| Паспорт / доступы | «паспорт проекта» / этот файл |
| Стиль блога | Onest + ivory + терракота уже в шаблоне и на live |

---

## 11. Связанные инструкции

| Тема | Файл |
|------|------|
| Каналы и очереди | `docs/content-channels.md` |
| Агент и cron | `docs/automation-agent.md` |
| RSS → Дзен | `checklists/dzen-rss-tilda.md` |
| VK фото / пауза | `checklists/vk-photo-token.md` |
| Обложки | `docs/covers-cloud-agent.md`, `checklists/covers-codex-pc.md` |
| Голос Марии | `references/maria-voice.md` |
| Расписание (текст) | `plan/posting-schedule.md` |
| Цвета бренда | `brandbook/colors.md`, `brandbook/tokens.json` |
| Правила агента | `AGENTS.md` |
