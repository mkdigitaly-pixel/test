# Паспорт проекта mkekspert (контент-автоматизация)

Куда что лежит и как зайти. **Секреты (токены) сюда не пишем** — только имена переменных и где они хранятся.

Обновлено: 2026-10-03.

---

## 1. Репозиторий и код

| Что | Значение |
|-----|----------|
| GitHub | https://github.com/mkdigitaly-pixel/test |
| SSH remote | `git@github.com:mkdigitaly-pixel/test.git` |
| Папка проекта в репо | `автоматизация-контента/` |
| Рабочая ветка агента (сейчас) | `cursor/schedule-catchup-8631` |
| Базовая ветка для PR | `cursor/rename-test-to-work-e9d0` (далее — по договорённости) |
| PR | https://github.com/mkdigitaly-pixel/test/pull/8 |

### Как открыть код у себя

1. GitHub → репозиторий `mkdigitaly-pixel/test`
2. Или на ПК: `git clone git@github.com:mkdigitaly-pixel/test.git`
3. Папка: `test/автоматизация-контента/`

---

## 2. Cloud Agent (Cursor)

| Что | Значение |
|-----|----------|
| Чат агента | https://cursor.com/agents/bc-95eaf9e4-d3bb-4ef3-9ef2-76fc8a2a8631 |
| Аккаунт владельца | mkdigitaly@gmail.com (Мария Ковалева) |
| Режим | Self-hosted / private worker |
| Таймер расписания | `schedule-run-daily` — cron `5 7,9,11 * * *` (UTC) → 10:05 / 12:05 / 14:05 МСК |

Агент сам запускает `python3 publish.py schedule run` по таймеру.

---

## 3. Сайты и каналы (публичные ссылки)

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

Основной сайт **mkekspert.ru** — Tilda (не этот блог).

---

## 4. Где лежат файлы (структура)

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
├── .env                   # флаги (например VK_PUBLISH) — не коммитить
├── automation/.env        # токены — не коммитить
└── ДОСТУПЫ.env            # Tilda / Webmaster — не коммитить
```

---

## 5. Секреты и доступы (где лежат, что означают)

**Не коммитить:** `.env`, `automation/.env`, `ДОСТУПЫ.env`.

| Файл | Что внутри (имена ключей) |
|------|---------------------------|
| `automation/.env` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MAIN_CHANNEL_ID`, `TELEGRAM_DZEN_CHANNEL_ID`, `VK_ACCESS_TOKEN`, `VK_USER_TOKEN`, `VK_GROUP_ID`, `VK_PHOTOS`, `VK_PUBLISH`, `AUTO_PUBLISH`, `DZEN_*`, Tilda-ключи (если скопированы) |
| `.env` (корень папки) | `VK_PUBLISH` (флаг паузы VK) |
| `ДОСТУПЫ.env` | `TILDA_*`, `WEBMASTER_YANDEX_VERIFICATION` |
| Образец без секретов | `automation/.env.example` |

### Важные флаги сейчас

| Флаг | Значение | Смысл |
|------|----------|--------|
| `AUTO_PUBLISH` | `true` | Расписание публикует по-настоящему |
| `VK_PHOTOS` | `manual` | В VK только текст; картинки крепит Мария |
| `VK_PUBLISH` | `off` | **Новые посты/тизеры VK не публикуются** (слоты ждут) |
| `DZEN_PUBLISH_MODE` | `auto` | Длинные статьи → RSS, короткие → zen_sync |
| `DZEN_RSS_DEPLOY_GH_PAGES` | `true` | После статьи — деплой на blog |

Чтобы снова публиковать VK: в `automation/.env` поставить `VK_PUBLISH=on` и написать агенту.

---

## 6. Как зайти в кабинеты

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

Логина/пароля Студии Дзена в `.env` **нет** — публикация статей через RSS.

---

## 7. Как публикуется (поток)

```
вт/чт 10:00  publish_dzen     → HTML + feed.xml → blog.mkekspert.ru → Дзен забирает RSS
вт/чт 12:00  publish_teasers  → TG тизер (+ VK тизер, если VK_PUBLISH=on)
пн/… 11:00   publish_tg_post  → @mariyaprodirect
сб/… 11:00   publish_vk_post  → VK (сейчас на паузе)
```

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

---

## 8. Обложки

| Размер | Файл | Куда |
|--------|------|------|
| 1200×630 | `assets/covers/{slug}.jpg` | Дзен / TG |
| 1080×1080 | `assets/covers/{slug}-vk.jpg` | VK вручную |

Стиль: тёмный бренд как в Telegram (`references/brand-visual.md`) — **без пластилина**.  
Готовые URL: `https://blog.mkekspert.ru/covers/{slug}-vk.jpg`.

---

## 9. Что сказать агенту (шпаргалка)

| Нужно | Фраза |
|-------|--------|
| Запустить расписание | «запусти schedule run» |
| Статус очереди | «что по расписанию?» |
| Снова публиковать VK | «включи VK_PUBLISH=on» |
| Не трогать VK | уже `VK_PUBLISH=off` |
| Картинка к VK-посту | «ссылку на обложку для поста #N» |
| Статья в блог/RSS | «опубликуй dzen &lt;id&gt;» |

---

## 10. Связанные инструкции

| Тема | Файл |
|------|------|
| Каналы и очереди | `docs/content-channels.md` |
| Агент и cron | `docs/automation-agent.md` |
| RSS → Дзен | `checklists/dzen-rss-tilda.md` |
| VK фото / пауза | `checklists/vk-photo-token.md` |
| Обложки | `docs/covers-cloud-agent.md`, `checklists/covers-codex-pc.md` |
| Голос Марии | `references/maria-voice.md` |
| Расписание (текст) | `plan/posting-schedule.md` |
