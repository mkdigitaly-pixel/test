#!/usr/bin/env python3
"""Сбор номенклатуры MiniMed с minimed.ru и minimed.nt-rt.ru."""

from __future__ import annotations

import json
import re
import time
from collections import OrderedDict
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
import xlrd
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CACHE = DATA / "cache"

BASE = "https://minimed.ru"
NTRT = "https://minimed.nt-rt.ru"
PRICE_XLS = BASE + "/price.xls"
CATALOG_PDF = BASE + "/catalog.pdf"
NTRT_PRICE_PDF = NTRT + "/images/showcase/pricelis.pdf"
NTRT_CATALOG_PDF = NTRT + "/images/showcase/katalogminimed.pdf"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DELAY = 0.45
VAT_DEFAULT = 22.0

HEADERS = [
    "Модель",
    "Наименование",
    "Категория",
    "Цена",
    "Артикул",
    "Ссылка на товар",
    "Источник",
]

ROOT_CATEGORIES = [
    "Лабораторная посуда и принадлежности из стекла",
    "Лабораторная посуда и принадлежности из пластика",
    "Лабораторная посуда и принадлежности из фарфора",
    "Лабораторная посуда и принадлежности прочие",
    "Лабораторное оборудование",
    "Пробирки вакуумные стерильные. Принадлежности для забора крови.",
    "Красители и химические реактивы",
    "Спецпредложение",
]

NTRT_SECTIONS = [
    (
        "Лабораторная посуда и принадлежности из стекла",
        NTRT + "/catalog/laboratornaya-posuda-i-prinadleznosti-iz-stekla",
    ),
    (
        "Лабораторная посуда и принадлежности из пластика",
        NTRT + "/catalog/laboratornaya-posuda-i-prinadleznosti-iz-plastika",
    ),
    (
        "Лабораторная посуда и принадлежности из фарфора",
        NTRT + "/catalog/laboratornaya-posuda-i-prinadleznosti-iz-farfora",
    ),
    (
        "Лабораторная посуда и принадлежности прочие",
        NTRT + "/catalog/laboratornaya-posuda-i-prinadleznosti-prochie",
    ),
    (
        "Лабораторное оборудование",
        NTRT + "/catalog/laboratornoe-oborudovanie",
    ),
    (
        "Пробирки вакуумные стерильные",
        NTRT + "/catalog/probirki-vakuumnye-sterilnye",
    ),
    (
        "Принадлежности для забора крови",
        NTRT + "/catalog/prinadleznosti-dlya-zabora-krovi",
    ),
    (
        "Красители и химические реактивы",
        NTRT + "/catalog/krasiteli-i-himiceskie-reaktivy",
    ),
]

# Первое слово группы (мн.ч.) → ед.ч. для наименования.
SINGULAR_FIRST = [
    (r"^Аквадистилляторы\b", "Аквадистиллятор"),
    (r"^Ареометры\b", "Ареометр"),
    (r"^Бани\b", "Баня"),
    (r"^Банки\b", "Банка"),
    (r"^Баллоны\b", "Баллон"),
    (r"^Бахилы\b", "Бахила"),
    (r"^Бинты\b", "Бинт"),
    (r"^Бутирометры\b", "Бутирометр"),
    (r"^Бутылки\b", "Бутылка"),
    (r"^Бутыли\b", "Бутыль"),
    (r"^Бюретки\b", "Бюретка"),
    (r"^Ванночки\b", "Ванночка"),
    (r"^Воронки\b", "Воронка"),
    (r"^Держатели\b", "Держатель"),
    (r"^Дозаторы\b", "Дозатор"),
    (r"^Емкости\b", "Емкость"),
    (r"^Ерши\b", "Ёрш"),
    (r"^Зажимы\b", "Зажим"),
    (r"^Иглы\b", "Игла"),
    (r"^Камеры\b", "Камера"),
    (r"^Капельницы\b", "Капельница"),
    (r"^Капилляры\b", "Капилляр"),
    (r"^Каплеуловители\b", "Каплеуловитель"),
    (r"^Кастрюли\b", "Кастрюля"),
    (r"^Ковши\b", "Ковш"),
    (r"^Колбы\b", "Колба"),
    (r"^Колпачки\b", "Колпачок"),
    (r"^Комплекты\b", "Комплект"),
    (r"^Контейнеры\b", "Контейнер"),
    (r"^Корзины\b", "Корзина"),
    (r"^Красители\b", "Краситель"),
    (r"^Кружки\b", "Кружка"),
    (r"^Кюветы\b", "Кювета"),
    (r"^Лампы\b", "Лампа"),
    (r"^Лодочки\b", "Лодочка"),
    (r"^Лопаточки\b", "Лопаточка"),
    (r"^Ложки\b", "Ложка"),
    (r"^Лотки\b", "Лоток"),
    (r"^Лупы\b", "Лупа"),
    (r"^Магниты\b", "Магнит"),
    (r"^Маски\b", "Маска"),
    (r"^Мензурки\b", "Мензурка"),
    (r"^Микроскопы\b", "Микроскоп"),
    (r"^Наконечники\b", "Наконечник"),
    (r"^Насадки\b", "Насадка"),
    (r"^Пакеты\b", "Пакет"),
    (r"^Палочки\b", "Палочка"),
    (r"^Переходы\b", "Переход"),
    (r"^Переходники\b", "Переходник"),
    (r"^Перчатки\b", "Перчатка"),
    (r"^Пестики\b", "Пестик"),
    (r"^Петли\b", "Петля"),
    (r"^Пикнометры\b", "Пикнометр"),
    (r"^Пинцеты\b", "Пинцет"),
    (r"^Пипетаторы\b", "Пипетатор"),
    (r"^Пипетки\b", "Пипетка"),
    (r"^Планшеты\b", "Планшет"),
    (r"^Пластины\b", "Пластина"),
    (r"^Плитки\b", "Плитка"),
    (r"^Полислайды\b", "Полислайд"),
    (r"^Приборы\b", "Прибор"),
    (r"^Пробирки\b", "Пробирка"),
    (r"^Пробки\b", "Пробка"),
    (r"^Промывалки\b", "Промывалка"),
    (r"^Растворы\b", "Раствор"),
    (r"^Салфетки\b", "Салфетка"),
    (r"^Скарификаторы\b", "Скарификатор"),
    (r"^Скальпели\b", "Скальпель"),
    (r"^Склянки-аспираторы\b", "Склянка-аспиратор"),
    (r"^Склянки\b", "Склянка"),
    (r"^Сосуды\b", "Сосуд"),
    (r"^Спиртовки\b", "Спиртовка"),
    (r"^Спринцовки\b", "Спринцовка"),
    (r"^Стаканчики\b", "Стаканчик"),
    (r"^Стаканы\b", "Стакан"),
    (r"^Ступки\b", "Ступка"),
    (r"^Счетчики\b", "Счетчик"),
    (r"^Секундомеры\b", "Секундомер"),
    (r"^Тампон-зонды\b", "Тампон-зонд"),
    (r"^Термометры\b", "Термометр"),
    (r"^Тигли\b", "Тигель"),
    (r"^Трубки\b", "Трубка"),
    (r"^Укладки\b", "Укладка"),
    (r"^Фильтры\b", "Фильтр"),
    (r"^Фитили\b", "Фитиль"),
    (r"^Флаконы\b", "Флакон"),
    (r"^Холодильники\b", "Холодильник"),
    (r"^Центрифуги\b", "Центрифуга"),
    (r"^Цилиндры\b", "Цилиндр"),
    (r"^Чаши\b", "Чаша"),
    (r"^Чашки\b", "Чашка"),
    (r"^Часы\b", "Часы"),
    (r"^Шапочки\b", "Шапочка"),
    (r"^Шпатели\b", "Шпатель"),
    (r"^Шприцы\b", "Шприц"),
    (r"^Штативы\b", "Штатив"),
    (r"^Щетки\b", "Щетка"),
    (r"^Щитки\b", "Щиток"),
    (r"^Эксикаторы\b", "Эксикатор"),
    (r"^Элементы\b", "Элемент"),
    (r"^Изгибы\b", "Изгиб"),
]

ADJ_PLURAL = [
    (r"\bлабораторные\b", "лабораторная"),
    (r"\bстеклянные\b", "стеклянная"),
    (r"\bпластиковые\b", "пластиковая"),
    (r"\bфарфоровые\b", "фарфоровая"),
    (r"\bвакуумные\b", "вакуумная"),
    (r"\bстерильные\b", "стерильная"),
    (r"\bнестерильные\b", "нестерильная"),
    (r"\bмедицинские\b", "медицинская"),
    (r"\bмерные\b", "мерная"),
    (r"\bградуированные\b", "градуированная"),
    (r"\bконические\b", "коническая"),
    (r"\bкруглодонные\b", "круглодонная"),
    (r"\bплоскодонные\b", "плоскодонная"),
    (r"\bделительные\b", "делительная"),
    (r"\bкерамические\b", "керамическая"),
    (r"\bметаллические\b", "металлическая"),
    (r"\bрезиновые\b", "резиновая"),
    (r"\bсиликоновые\b", "силиконовая"),
    (r"\bпоршневые\b", "поршневая"),
    (r"\bэлектрические\b", "электрическая"),
    (r"\bзащитные\b", "защитная"),
    (r"\bпроцедурные\b", "процедурная"),
    (r"\bпсихрометрические\b", "психрометрическая"),
    (r"\bгистологические\b", "гистологическая"),
    (r"\bмикробиологические\b", "микробиологическая"),
    (r"\bсерологические\b", "серологическая"),
    (r"\bбактериологические\b", "бактериологическая"),
    (r"\bинъекционные\b", "инъекционная"),
    (r"\bофисные\b", "офисная"),
    (r"\bфильтровальные\b", "фильтровальная"),
    (r"\bбуферные\b", "буферный"),
    (r"\bхимические\b", "химический"),
    (r"^Буферные растворы\b", "Буферный раствор"),
]


def cell(value) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"[\t\r\n]+", " ", unescape(text)).strip()


def norm_art(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "g")
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".", 1)[0]
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def parse_money(raw) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw)
    text = text.replace("\xa0", " ").replace(" ", "").replace("руб.", "").replace("руб", "")
    text = text.replace(",", ".")
    text = re.sub(r"[^0-9.]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def price_without_vat(gross, vat) -> str:
    amount = parse_money(gross)
    if amount is None or amount <= 0:
        return ""
    rate = 0.0
    if vat is None or vat == "":
        rate = VAT_DEFAULT
    elif isinstance(vat, (int, float)):
        rate = float(vat)
    else:
        text = str(vat).strip().lower().replace("%", "").replace(",", ".")
        if "без" in text:
            rate = 0.0
        else:
            m = re.search(r"(\d+(?:\.\d+)?)", text)
            rate = float(m.group(1)) if m else VAT_DEFAULT
    if rate > 0:
        amount = amount / (1.0 + rate / 100.0)
    return str(int(round(amount)))


def singular_type(group: str) -> str:
    name = cell(group)
    if not name:
        return ""
    for pat, repl in SINGULAR_FIRST:
        if re.search(pat, name, flags=re.I):
            name = re.sub(pat, repl, name, count=1, flags=re.I)
            break
    # согласовать первое прилагательное после существительного
    parts = name.split(" ", 1)
    if len(parts) == 2:
        head, rest = parts
        for pat, repl in ADJ_PLURAL:
            rest = re.sub(pat, repl, rest, count=1, flags=re.I)
        name = f"{head} {rest}"
    return name


MODEL_RE = re.compile(
    r"""
    (
        [А-ЯA-ZЁ]{1,6}          # буквенный префикс
        (?:[A-ZА-ЯЁ]{0,4})?
        [\-\s]?
        \d[\d\./xх\*×,\-]*      # типоразмер
        (?:[A-ZА-ЯЁ]{0,4})?
      |
        \d+(?:-\d+){2,}(?:-[\d,]+)*   # ГОСТ-код бюретки/пипетки 1-1-2-10-0,05
    )
    """,
    re.VERBOSE,
)

VOLUME_ONLY_RE = re.compile(
    r"^(?:\d+(?:[.,]\d+)?\s*(?:мкл|мл|л|мм|см|г|кг|шт)\b.*)$",
    re.I,
)


def extract_model(raw_name: str, site_name: str = "") -> str:
    blob = cell(raw_name)
    main = blob.split(";")[0].strip()
    main = re.sub(r"\([^)]*\)", " ", main).strip()
    main = re.sub(r"\s+", " ", main)
    if not main:
        blob2 = cell(site_name)
        main = blob2.split(",")[0].strip()
    if VOLUME_ONLY_RE.match(main):
        # объём + габарит — это типоразмер (8 мл, 16x100 мм)
        cleaned = re.sub(r",?\s*спецзаказ\s*$", "", main, flags=re.I).strip(" ,;")
        if re.search(r"\d+\s*[xх\*×]\s*\d+", cleaned):
            return cell(cleaned.replace("*", "x").replace("×", "x").replace("х", "x"))
        return ""
    # короткое обозначение целиком
    if re.fullmatch(r"[А-ЯA-ZЁ0-9][А-ЯA-ZЁ0-9\d\./xх\*×,\-\s]{1,40}", main) and re.search(
        r"\d", main
    ):
        # отсечь слишком описательные фразы
        if len(main.split()) <= 5 and not re.search(
            r"\b(для|из|с|со|без|под|на|по)\b", main, re.I
        ):
            return cell(main)
    m = MODEL_RE.search(main)
    if m:
        model = cell(m.group(1))
        model = model.replace("х", "x").replace("×", "x").replace("*", "x")
        model = re.sub(r"\s+", " ", model)
        if len(model) >= 3:
            return model
    # модель из названия сайта, если в прайсе только объём
    if site_name:
        m2 = MODEL_RE.search(cell(site_name))
        if m2:
            model = cell(m2.group(1))
            if len(model) >= 3 and not VOLUME_ONLY_RE.match(model):
                return model
    return ""


def strip_model(name: str, model: str) -> str:
    text = cell(name)
    if not text:
        return ""
    text = re.sub(r"\bминимед\b", " ", text, flags=re.I)
    text = re.sub(r"\bminimed\b", " ", text, flags=re.I)
    if model:
        variants = {model, model.replace("x", "х"), model.replace("х", "x")}
        for var in variants:
            text = re.sub(re.escape(var), " ", text, flags=re.I)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"^[\s,;./\-]+", "", text)
    text = re.sub(r"[\s,;]+$", "", text)
    # убрать пустые скобки
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;")
    return cell(text)


def build_name(site_name: str, xls_name: str, group: str, model: str) -> str:
    if site_name:
        name = strip_model(site_name, model)
    else:
        xls = cell(xls_name)
        main, *rest = [p.strip() for p in xls.split(";") if p.strip()]
        pack = ""
        extra = []
        for part in rest:
            if part.lower().startswith("уп"):
                pack = part
            else:
                extra.append(part)
        if VOLUME_ONLY_RE.match(main) or (model and main.replace(" ", "") == model.replace(" ", "")):
            body = singular_type(group)
            bits = [body]
            if VOLUME_ONLY_RE.match(main):
                bits.append(main)
            elif extra:
                bits.extend(extra)
            elif main and not model:
                bits.append(main)
            name = ", ".join(b for b in bits if b)
            if pack:
                name = f"{name}, {pack}"
        else:
            # описание в прайсе: «для молока» в скобках
            desc = ""
            m = re.search(r"\(([^)]+)\)", xls)
            if m:
                desc = m.group(1).strip()
            body = singular_type(group)
            bits = [body]
            leftover = strip_model(main, model)
            leftover = leftover.strip(" ;,")
            if leftover and leftover.lower() not in body.lower():
                bits.append(leftover)
            if desc and desc.lower() not in " ".join(bits).lower():
                bits.append(desc)
            name = ", ".join(b for b in bits if b)
            if pack:
                name = f"{name}, {pack}"
        name = strip_model(name, model)
    name = re.sub(r"\s{2,}", " ", name).strip(" ,;")
    # ед.ч. уже в типе; не укорачивать формулировку
    if name and name[0].islower():
        name = name[0].upper() + name[1:]
    return name


def is_root_category(name: str) -> bool:
    n = cell(name).rstrip(".")
    for root in ROOT_CATEGORIES:
        if n == root.rstrip(".") or name.strip() == root:
            return True
        if name.strip().startswith("Пробирки вакуумные стерильные"):
            return True
    return False


class Http:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"})

    def get(self, url: str, retries: int = 4) -> requests.Response:
        last = None
        for i in range(retries):
            try:
                time.sleep(DELAY)
                r = self.s.get(url, timeout=60)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 * (i + 1))
                    last = r
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as exc:
                last = exc
                time.sleep(2 * (i + 1))
        if isinstance(last, requests.Response):
            last.raise_for_status()
        raise last  # type: ignore

    def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 1000:
            return dest
        print(f"  download {url}")
        r = self.get(url)
        dest.write_bytes(r.content)
        return dest


def parse_catalog_tree(html: str) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Корни и листья (root_name, leaf_name, url)."""
    soup = BeautifulSoup(html, "lxml")
    roots: list[tuple[str, str]] = []
    leaves: list[tuple[str, str, str]] = []
    # боковое меню каталога
    for root_li in soup.select("ul li"):
        pass
    # надёжнее: все ссылки /catalog/x/ и /catalog/x/y/
    seen = set()
    root_map: OrderedDict[str, str] = OrderedDict()
    for a in soup.select('a[href^="/catalog/"]'):
        href = a.get("href", "").split("?")[0]
        if not href.endswith("/"):
            href += "/"
        if any(x in href for x in ("/tag/", "/discount/", "/lider/", "/new/", "/sale/")):
            continue
        parts = [p for p in href.strip("/").split("/") if p]
        if len(parts) < 2:
            continue
        name = cell(a.get_text())
        if not name or name.lower() in {"каталог", "подробнее"}:
            continue
        if href in seen:
            continue
        seen.add(href)
        url = urljoin(BASE, href)
        if len(parts) == 2:
            root_map[parts[1]] = name
            roots.append((name, url))
        elif len(parts) >= 3:
            root_name = root_map.get(parts[1], "")
            leaves.append((root_name, name, url))
    return roots, leaves


def pager_pages(html: str, page_url: str) -> list[str]:
    pages = {page_url}
    for m in re.finditer(r"PAGEN_1=(\d+)", html):
        n = int(m.group(1))
        if n > 1:
            sep = "&" if "?" in page_url else "?"
            # drop existing PAGEN
            base = re.sub(r"([?&])PAGEN_1=\d+", "", page_url).rstrip("&?")
            sep = "&" if "?" in base else "?"
            pages.add(f"{base}{sep}PAGEN_1={n}")
    # sequential 1..max
    nums = [1]
    for u in list(pages):
        m = re.search(r"PAGEN_1=(\d+)", u)
        if m:
            nums.append(int(m.group(1)))
    max_n = max(nums)
    out = []
    base = re.sub(r"([?&])PAGEN_1=\d+", "", page_url).rstrip("&?")
    for n in range(1, max_n + 1):
        if n == 1:
            out.append(base)
        else:
            sep = "&" if "?" in base else "?"
            out.append(f"{base}{sep}PAGEN_1={n}")
    return out


def parse_listing(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for card in soup.select(".product_card"):
        title_a = card.select_one(".product__title a, a.s_name")
        if not title_a or not title_a.get("href"):
            continue
        href = urljoin(BASE, title_a["href"])
        name = cell(title_a.get("title") or title_a.get_text())
        art = ""
        art_el = card.select_one(".product__article")
        if art_el:
            art = norm_art(re.sub(r"артикул:\s*", "", art_el.get_text(" ", strip=True), flags=re.I))
        price = None
        val = card.select_one(".product__price .value")
        if val:
            price = parse_money(val.get_text())
        items.append({"name": name, "url": href, "article": art, "price": price})
    if items:
        return items
    # JSON-LD fallback
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            stack.extend(node.values())
            if node.get("@type") == "Product" and node.get("url"):
                offers = node.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                items.append(
                    {
                        "name": cell(node.get("name")),
                        "url": urljoin(BASE, str(node.get("url"))),
                        "article": norm_art(node.get("mpn") or node.get("sku") or ""),
                        "price": parse_money(offers.get("price")),
                    }
                )
    return items


def crawl_site(http: Http) -> dict[str, dict]:
    """article -> {name, url, price, category}."""
    print("Каталог minimed.ru …")
    html = http.get(BASE + "/catalog/").text
    roots, leaves = parse_catalog_tree(html)
    print(f"  корней {len(roots)}, листьев {len(leaves)}")
    by_art: dict[str, dict] = {}
    for i, (root_name, leaf_name, url) in enumerate(leaves, 1):
        category = "/".join(p for p in (root_name, leaf_name) if p)
        try:
            page1 = http.get(url).text
        except Exception as exc:
            print(f"  skip {url}: {exc}")
            continue
        pages = pager_pages(page1, url)
        htmls = [page1]
        for p in pages[1:]:
            try:
                htmls.append(http.get(p).text)
            except Exception as exc:
                print(f"  skip {p}: {exc}")
        for h in htmls:
            for item in parse_listing(h):
                art = item["article"]
                if not art:
                    continue
                rec = {
                    "name": item["name"],
                    "url": item["url"],
                    "price": item["price"],
                    "category": category,
                }
                if art not in by_art:
                    by_art[art] = rec
        if i == 1 or i % 20 == 0 or i == len(leaves):
            print(f"  [{i}/{len(leaves)}] {leaf_name}: карточек {len(by_art)}")
    print(f"  итого карточек: {len(by_art)}")
    return by_art


def parse_price_xls(path: Path) -> list[dict]:
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)
    rows = []
    root = ""
    group = ""
    for r in range(5, sh.nrows):
        art = norm_art(sh.cell_value(r, 0))
        name = cell(sh.cell_value(r, 1))
        if not art and not name:
            continue
        if not art:
            if is_root_category(name):
                root = name
                group = ""
            else:
                group = name
            continue
        vat = sh.cell_value(r, 2)
        wholesale = sh.cell_value(r, 5)
        cat = "/".join(p for p in (root, group) if p)
        rows.append(
            {
                "article": art,
                "xls_name": name,
                "root": root,
                "group": group,
                "category": cat,
                "vat": vat,
                "wholesale": wholesale,
            }
        )
    return rows


def pdf_articles(path: Path) -> set[str]:
    arts: set[str] = set()
    try:
        import pdfplumber
    except ImportError:
        return arts
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            arts.update(re.findall(r"\b(\d{8})\b", text))
    return arts


def write_tsv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("\t".join(HEADERS) + "\n")
        for row in rows:
            f.write("\t".join(row) + "\n")


def write_xlsx(path: Path, rows: list[list[str]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Номенклатура"
    ws.append(HEADERS)
    for cell_ in ws[1]:
        cell_.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    ws.auto_filter.ref = f"A1:G{ws.max_row}"
    ws.freeze_panes = "A2"
    wb.save(path)


def ntrt_fallback(category: str) -> str:
    cat = category.split("/")[0] if category else ""
    for name, url in NTRT_SECTIONS:
        if cat.startswith(name.split(".")[0]) or name.startswith(cat.split(".")[0]):
            return url
    return NTRT + "/catalog"


def assemble(xls_rows: list[dict], site: dict[str, dict], extra_arts: set[str]) -> list[list[str]]:
    used = set()
    out: list[list[str]] = []
    prev_cat = None
    first = True

    def emit_group(cat: str):
        nonlocal first, prev_cat
        if prev_cat == cat:
            return
        if not first:
            out.append(["", "", "", "", "", "", ""])
        out.append([cat, "", "", "", "", "", ""])
        prev_cat = cat
        first = False

    for rec in xls_rows:
        art = rec["article"]
        site_rec = site.get(art) or {}
        model = extract_model(rec["xls_name"], site_rec.get("name", ""))
        name = build_name(site_rec.get("name", ""), rec["xls_name"], rec["group"] or rec["root"], model)
        cat = rec["category"] or site_rec.get("category") or rec["root"]
        price = price_without_vat(rec["wholesale"] or site_rec.get("price"), rec["vat"])
        url = site_rec.get("url") or ""
        if url:
            source = "minimed.ru"
        else:
            url = ntrt_fallback(cat)
            source = "minimed.ru (прайс)"
        emit_group(cat)
        out.append([cell(model), cell(name), cell(cat), price, art, url, source])
        used.add(art)

    # товары сайта, которых нет в прайсе
    extras = []
    for art, rec in site.items():
        if art in used:
            continue
        extras.append((rec.get("category") or "Прочее", rec, art))
    extras.sort(key=lambda x: (x[0], x[2]))
    for cat, rec, art in extras:
        model = extract_model("", rec.get("name", ""))
        name = build_name(rec.get("name", ""), "", cat.split("/")[-1], model)
        price = price_without_vat(rec.get("price"), VAT_DEFAULT)
        emit_group(cat)
        out.append(
            [
                cell(model),
                cell(name),
                cell(cat),
                price,
                art,
                rec.get("url", ""),
                "minimed.ru",
            ]
        )
        used.add(art)

    # PDF нужен для проверки покрытия: не добавляем безымянные 8-значные номера.
    _ = extra_arts
    return out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    http = Http()

    xls_path = http.download(PRICE_XLS, CACHE / "price.xls")
    print("Разбор price.xls …")
    xls_rows = parse_price_xls(xls_path)
    print(f"  позиций в прайсе: {len(xls_rows)}")

    site = crawl_site(http)
    print(f"  карточек на сайте: {len(site)}")

    extra_arts: set[str] = set()
    for url, name in (
        (NTRT_CATALOG_PDF, "ntrt-katalog.pdf"),
        (NTRT_PRICE_PDF, "ntrt-pricelis.pdf"),
        (CATALOG_PDF, "catalog.pdf"),
    ):
        try:
            path = http.download(url, CACHE / name)
            arts = pdf_articles(path)
            print(f"  {name}: артикулов {len(arts)}")
            extra_arts |= arts
        except Exception as exc:
            print(f"  {name}: {exc}")

    rows = assemble(xls_rows, site, extra_arts)
    goods = [r for r in rows if r[4]]
    tsv = DATA / "nomenclature.tsv"
    xlsx = DATA / "nomenclature.xlsx"
    write_tsv(tsv, rows)
    write_xlsx(xlsx, rows)
    print(f"Готово: {len(goods)} товаров → {tsv}")


if __name__ == "__main__":
    main()
