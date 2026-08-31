# MiniMed — номенклатура

Источники:

- https://minimed.ru/ — каталог завода, прайс `price.xls`, каталог `catalog.pdf`
- https://minimed.nt-rt.ru/ — витрина NT-RT, PDF-прайс и каталог

## Запуск

```bash
cd parser/minimed
pip install -r requirements.txt
python parse_all.py
```

Результат: `data/nomenclature.tsv` и `data/nomenclature.xlsx`.

Колонки: `Модель`, `Наименование`, `Категория`, `Цена`, `Артикул`, `Ссылка на товар`, `Источник`.

Цена — оптовая **без НДС** (ставка 22% / 10% / без НДС из прайса завода), целое число без пробелов.

## Кэш

Скачанные прайсы и PDF кладутся в `data/cache/` (не в git).
