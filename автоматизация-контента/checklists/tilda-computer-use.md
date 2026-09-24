# Чеклист: Tilda + Computer Use

Документ: [`docs/tilda-computer-use.md`](../docs/tilda-computer-use.md)

## Один раз

- [ ] Cursor с **Computer Use / Browser** (не только cloud без браузера)
- [ ] В браузере агента залогинена Tilda (аккаунт владельца или редактора mkekspert)
- [ ] Виден проект **Мария Ковалева** / mkekspert.ru
- [ ] В `ДОСТУПЫ.env` ключи API (для проверки после правок) — уже есть
- [ ] Правило агента: `.cursor/rules/tilda-computer-use.mdc`

## На каждую задачу

- [ ] Назвать страницу (например `razbor-direct`)
- [ ] Агент правит → **Save**
- [ ] Показать результат (скрин / описание)
- [ ] Публикация только после фразы вроде «публикуй» / «да, публикуем»

## Первая боевая задача (когда Computer Use есть)

1. Открыть `razbor-direct`
2. Вставить / заменить контент из `content/tilda-razbor-direct.html`
3. Save
4. Спросить про Publish
5. После Publish — проверить https://mkekspert.ru/razbor-direct

## Пока Computer Use нет в этой среде

Агент **не** может кликать Tilda. Временный путь: ручная вставка HTML по `content/tilda-razbor-direct.md`.
