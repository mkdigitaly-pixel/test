"""Разбор таблиц заводского catalog.pdf MiniMed."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

ART = re.compile(r"\d{8}")
ROW = re.compile(
    r"^\s*(?:\d{1,3}\s+)?(\d{8})(?:\s*/\s*(\d{8}))?\s*(?:/\s*)?(.*)$"
)
STANDALONE = re.compile(r"^Артикул\s+(\d{8})\b", re.I)
NUM_HEAD = re.compile(r"^\d+\.\s+(.+)$")

SKIP_PREFIX = (
    "гост",
    "ту ",
    "ту-",
    "ру №",
    "производитель",
    "предназнач",
    "изготовлен",
    "упаковка",
    "артикул",
    "наименование",
    "материал",
    "маркировка",
    "допустим",
    "номинальн",
    "приложение",
    "содержание",
    "алфавитн",
    "артикулярн",
    "лабораторная посуда и принадлежности",
    "н —",
    "класс точности",
    "используются",
    "разработаны",
    "ориентировочн",
    "смотри стр",
    "продолжение",
    "химические реактивы",
)

ROOT_BY_CONTENT = [
    (3, 44, "Лабораторная посуда и принадлежности из стекла"),
    (45, 97, "Лабораторная посуда и принадлежности из пластика"),
    (98, 103, "Лабораторная посуда и принадлежности из фарфора"),
    (104, 128, "Лабораторная посуда и принадлежности прочие"),
    (129, 139, "Лабораторное оборудование"),
    (140, 145, "Красители и химические реактивы"),
    (146, 157, "Пробирки вакуумные стерильные. Принадлежности для забора крови."),
    (158, 162, "Принадлежности для защиты персонала"),
    (163, 168, "Принадлежности для ПЦР"),
    (169, 172, "Лабораторная посуда 1 класса точности"),
]


def _cell(value: str) -> str:
    return re.sub(r"[\t\r\n]+", " ", value or "").strip()


def pdf_root(pdf_page: int) -> str:
    content = pdf_page - 2
    for a, b, name in ROOT_BY_CONTENT:
        if a <= content <= b:
            return name
    return ""


def _singular_first(name: str) -> str:
    repl = [
        (r"^Ареометры\b", "Ареометр"),
        (r"^Банки\b", "Банка"),
        (r"^Бюретки\b", "Бюретка"),
        (r"^Воронки\b", "Воронка"),
        (r"^Дозаторы\b", "Дозатор"),
        (r"^Емкости\b", "Емкость"),
        (r"^Камеры\b", "Камера"),
        (r"^Капельницы\b", "Капельница"),
        (r"^Капилляры\b", "Капилляр"),
        (r"^Колбы\b", "Колба"),
        (r"^Кюветы\b", "Кювета"),
        (r"^Лопаточки\b", "Лопаточка"),
        (r"^Мензурки\b", "Мензурка"),
        (r"^Наконечники\b", "Наконечник"),
        (r"^Пипетки\b", "Пипетка"),
        (r"^Пробки\b", "Пробка"),
        (r"^Пробирки\b", "Пробирка"),
        (r"^Склянки\b", "Склянка"),
        (r"^Стаканы\b", "Стакан"),
        (r"^Стаканчики\b", "Стаканчик"),
        (r"^Тигли\b", "Тигель"),
        (r"^Трубки\b", "Трубка"),
        (r"^Фиксаналы\b", "Фиксанал"),
        (r"^Цилиндры\b", "Цилиндр"),
        (r"^Чаши\b", "Чаша"),
        (r"^Чашки\b", "Чашка"),
        (r"^Часы\b", "Часы"),
        (r"^Эксикаторы\b", "Эксикатор"),
        (r"^Элементы\b", "Элемент"),
        (r"^Вставки\b", "Вставка"),
        (r"^Наборы\b", "Набор"),
        (r"^Красители\b", "Краситель"),
        (r"^Растворы\b", "Раствор"),
    ]
    text = name
    for pat, to in repl:
        if re.search(pat, text, re.I):
            text = re.sub(pat, to, text, count=1, flags=re.I)
            break
    text = re.sub(r"\bлабораторные\b", "лабораторная", text, count=1, flags=re.I)
    text = re.sub(r"\bделительные\b", "делительная", text, count=1, flags=re.I)
    text = re.sub(r"\bмерные\b", "мерная", text, count=1, flags=re.I)
    text = re.sub(r"\bконические\b", "коническая", text, count=1, flags=re.I)
    text = re.sub(r"\bцилиндрические\b", "цилиндрическая", text, count=1, flags=re.I)
    text = re.sub(r"\bцентрифужные\b", "центрифужная", text, count=1, flags=re.I)
    text = re.sub(r"\bстеклянные\b", "стеклянная", text, count=1, flags=re.I)
    text = re.sub(r"\bвакуумные\b", "вакуумная", text, count=1, flags=re.I)
    text = re.sub(r"\bплоскодонные\b", "плоскодонная", text, count=1, flags=re.I)
    text = re.sub(r"\bкруглодонные\b", "круглодонная", text, count=1, flags=re.I)
    if text.startswith("Цилиндр "):
        text = text.replace("мерная", "мерный").replace("цилиндрическая", "цилиндрический")
    if text.startswith("Пробка "):
        text = text.replace("литые", "литая").replace("пустотелые", "пустотелая")
    if text.startswith("Часы "):
        text = text.replace("песочная", "песочные")
    text = re.sub(r"^\d+\.\s*", "", text)
    return _cell(text)


def is_heading(line: str) -> bool:
    text = _cell(line)
    m = NUM_HEAD.match(text)
    if m:
        text = _cell(m.group(1))
    if len(text) < 5 or len(text) > 110:
        return False
    low = text.lower()
    if any(low.startswith(p) for p in SKIP_PREFIX):
        return False
    if ART.search(text) and re.search(r"^\d{8}\b", text):
        return False
    if re.fullmatch(r"\d+", text):
        return False
    if low.startswith("тип ") and len(text) < 40:
        return False
    if not re.match(r"[А-ЯЁA-Z«\"0-9]", text):
        return False
    if low.startswith("для ") or low.startswith("из "):
        return False
    if any(x in low for x in ("приобрета", "изготовлен", "поставля", "применяет", "в состав", "толщина", "предназнач", "состо")):
        return False
    if text.count(" ") > 8:
        return False
    return True


def looks_like_model(token: str) -> bool:
    t = token.replace("–", "-").replace("—", "-").strip(",;")
    if len(t) < 2 or not re.search(r"\d", t):
        return False
    if re.fullmatch(r"\d+(?:[.,]\d+)?", t):
        return False
    if re.fullmatch(r"\d+(?:-\d+)+(?:/\d+)?(?:,\d+)?", t):
        return True
    if re.match(r"^[А-ЯA-Zа-яё]{1,8}-?\d", t):
        return True
    if t.upper().startswith(("КШ-", "ПЗК-", "ЧПН", "К2Е", "К3Е", "ВД-", "КН-", "ПМ2")):
        return True
    return False


def split_model_rest(rest: str) -> tuple[str, str]:
    rest = _cell(rest).replace("–", "-").replace("—", "-")
    rest = re.sub(r"^/\s*", "", rest)
    if not rest or rest.lower().startswith("предназнач"):
        return "", ""
    m_chpn = re.match(r"^(ЧПН)\s*-\s*(\d+)", rest, re.I)
    if m_chpn:
        return f"ЧПН-{m_chpn.group(2)}", ""
    parts = rest.split()
    if parts and looks_like_model(parts[0].strip(",;")):
        model = parts[0].strip(",;")
        leftover = " ".join(parts[1:])
        leftover = re.sub(r"^[\d\s.,±xх*/\-]+", "", leftover)
        leftover = re.sub(r"\b\d+/\d+\b", " ", leftover)
        leftover = re.sub(r"\s{2,}", " ", leftover).strip(" ,;")
        if leftover.lower().startswith(("от ", "±")):
            leftover = ""
        return _cell(model), _cell(leftover)
    # название с существительного: «Фиксанал …», «Фенол …»
    if re.match(r"[А-ЯЁа-яёA-Z]", rest):
        # отрезать фасовку в конце не обязательно
        name = re.split(r"\s{2,}|\s(?=\d+\s*(?:кг|г|л|мл|амп))", rest, maxsplit=1)[0]
        return "", _cell(name if len(name) > 3 else rest)
    return "", ""


def parse_catalog_pdf(path: Path, catalog_url: str) -> list[dict]:
    products: dict[str, dict] = {}
    heading = ""
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            pdf_page = i + 1
            text = page.extract_text() or ""
            if pdf_page >= 176 and (
                "Артикулярный указатель" in text or "Алфавитный указатель" in text
            ):
                continue
            root = pdf_root(pdf_page)
            if not root:
                continue
            for raw in text.splitlines():
                line = _cell(raw)
                if not line:
                    continue
                sm = STANDALONE.match(line)
                if sm:
                    art = sm.group(1)
                    name = _singular_first(heading) or "Изделие"
                    products.setdefault(
                        art,
                        {
                            "article": art,
                            "model": "",
                            "name": name,
                            "category": "/".join(p for p in (root, heading) if p),
                            "source": "minimed.ru (PDF-каталог)",
                            "url": catalog_url,
                        },
                    )
                    continue
                if is_heading(line):
                    h = NUM_HEAD.sub(r"\1", line)
                    h = re.sub(r"\s*\(.*\)$", "", h).strip()
                    if 5 <= len(h) <= 100:
                        heading = h
                    continue
                m = ROW.match(line)
                if not m:
                    continue
                arts = [m.group(1)]
                if m.group(2):
                    arts.append(m.group(2))
                model, extra = split_model_rest(m.group(3) or "")
                name = extra
                if not name or re.match(r"^[\d\s.,±xх/\-]+$", name):
                    name = _singular_first(heading)
                if name and heading and name.lower() == extra.lower() and extra:
                    pass
                elif not extra and heading:
                    name = _singular_first(heading)
                if extra and heading and extra[0].islower():
                    name = _singular_first(heading)
                if extra and re.match(r"[А-ЯЁ]", extra) and len(extra) > 8:
                    name = extra
                    if name and name[0].islower():
                        name = name[0].upper() + name[1:]
                    # ед.ч. если начинается с мн.ч. группы
                    name = _singular_first(name)
                if not name:
                    name = _singular_first(heading) or "Изделие"
                cat = "/".join(p for p in (root, heading) if p)
                for art in arts:
                    products.setdefault(
                        art,
                        {
                            "article": art,
                            "model": model,
                            "name": name,
                            "category": cat,
                            "source": "minimed.ru (PDF-каталог)",
                            "url": catalog_url,
                        },
                    )
    return list(products.values())
