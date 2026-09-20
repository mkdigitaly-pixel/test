# Чеклист: куда вписать API и доступы

Секреты храним **только** в:

```
автоматизация-контента/automation/.env
```

Этот файл **не коммитится** (см. `.gitignore`).  
Шаблон полей: [`automation/.env.example`](../automation/.env.example)

---

## Как заполнить

1. Открой `automation/.env` (если нет — скопируй из `.env.example`)
2. Впиши значения после `=`
3. Напиши агенту: «ключи вписал» — проверю чтение без публикации секретов в чат

**Не присылай** пароли и ключи в Telegram/чат целиком — только в `.env` на сервере.

---

## Tilda

| Переменная | Где взять | Зачем агенту |
|------------|-----------|--------------|
| `TILDA_PUBLIC_KEY` | Tilda → Настройки сайта → **Экспорт → API** (тариф **Business**) | читать список страниц / HTML |
| `TILDA_SECRET_KEY` | там же | то же |
| `TILDA_PROJECT_ID` | в URL редактора или ответ `getprojectslist` | какой сайт |
| `TILDA_PAGE_RAZBOR_ID` | id страницы razbor-direct | точечный экспорт |

⚠️ Официальный API Tilda — **только чтение/экспорт**. Править блоки и публиковать через API **нельзя**.  
Логин/пароль Tilda в `.env` **не нужны** и не рекомендуются.

Чтобы агент **сам** правил Tilda: нужен контур Browser / Computer Use — см. [`docs/tilda-computer-use.md`](../docs/tilda-computer-use.md).
API-ключи тогда для проверки после правок, не для записи.

---

## Уже используемые каналы

| Блок | Переменные |
|------|------------|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MAIN_CHANNEL_ID`, `TELEGRAM_DZEN_CHANNEL_ID` |
| VK | `VK_ACCESS_TOKEN`, `VK_GROUP_ID`, `VK_USER_TOKEN` |
| Дзен / blog | `DZEN_*`, `GITHUB_REPO` |
| SEO съём позиций | `SEO_SERP_PROVIDER`, `SEO_SERP_USER`, `SEO_SERP_KEY` |
| Обложки | `OPENROUTER_API_KEY` |

---

## Опционально позже

| Переменная | Зачем |
|------------|--------|
| `YANDEX_WEBMASTER_TOKEN` | запросы/индекс (если подключим API Вебмастера) |
| `YANDEX_METRIKA_TOKEN` | отчёты Метрики |
| `YANDEX_METRIKA_COUNTER_ID` | сейчас на blog: `97606312` |

---

## Проверка агентом

```bash
cd автоматизация-контента/automation
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv('.env')
keys=['TILDA_PUBLIC_KEY','TILDA_SECRET_KEY','TILDA_PROJECT_ID','TELEGRAM_BOT_TOKEN','VK_ACCESS_TOKEN','SEO_SERP_KEY']
for k in keys:
    v=os.getenv(k) or ''
    print(f'{k}: {\"OK set\" if v.strip() else \"empty\"}')
"
```

Секреты в вывод не печатаются — только OK / empty.
