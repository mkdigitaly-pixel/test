#!/usr/bin/env python3
"""
SEO-пайплайн mkekspert: аудит готовности, банк ключей, позиции, отчёты.

  python3 seo_pipeline.py audit
  python3 seo_pipeline.py keywords list
  python3 seo_pipeline.py keywords add --query "..." [--url ...] [--pillar P1]
  python3 seo_pipeline.py positions record --query "..." --pos 12
  python3 seo_pipeline.py positions import ../seo/positions/2026-09-19.yaml
  python3 seo_pipeline.py positions fetch
  python3 seo_pipeline.py report
  python3 seo_pipeline.py status
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SEO_DIR = ROOT / "seo"
CONFIG_PATH = SEO_DIR / "config.yaml"
KEYWORDS_PATH = SEO_DIR / "keywords.yaml"
POSITIONS_DIR = SEO_DIR / "positions"
REPORTS_DIR = SEO_DIR / "reports"

UA = "mkekspert-seo-pipeline/1.0 (+https://mkekspert.ru)"


def load_dotenv_local() -> None:
    env = Path(__file__).resolve().parent / ".env"
    if env.exists():
        load_dotenv(env)


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Ожидался mapping в {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def http_get(url: str, timeout: int = 20) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "ignore")
            return int(resp.status), str(resp.geturl()), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore") if e.fp else ""
        return int(e.code), url, body
    except Exception as e:  # noqa: BLE001
        return 0, url, str(e)


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    return s[:60].strip("-") or "keyword"


# --- audit -----------------------------------------------------------------


def cmd_audit(_args: argparse.Namespace) -> int:
    cfg = read_yaml(CONFIG_PATH)
    sites = cfg.get("sites") or {}
    main = sites.get("main") or {}
    blog = sites.get("blog") or {}
    checks: list[tuple[str, bool, str]] = []

    def ok(name: str, passed: bool, detail: str) -> None:
        checks.append((name, passed, detail))

    # main home
    code, final, html = http_get(main.get("host", "https://mkekspert.ru/"))
    ok("main_reachable", code == 200, f"HTTP {code} → {final}")
    has_blog_link = "blog.mkekspert.ru" in html.lower()
    ok(
        "blog_link_on_main",
        has_blog_link,
        "ссылка на blog.mkekspert.ru есть"
        if has_blog_link
        else "НЕТ ссылки на блог с главной Tilda — добавить в подвал",
    )
    ok("metrika_on_main", "mc.yandex" in html.lower() or "ym(" in html, "Метрика")

    # www redirect: оба хоста с 200 без склейки — плохо для органики
    www_code, www_final, _ = http_get("https://www.mkekspert.ru/")
    www_stays = www_code == 200 and "www.mkekspert.ru" in www_final
    ok(
        "www_canonical",
        not www_stays,
        f"www → {www_final} (код {www_code})"
        if not www_stays
        else "www и без www оба отдают 200 — нужен редирект на один хост",
    )

    # sitemap https
    sm_code, _, sm_body = http_get(main.get("sitemap", "https://mkekspert.ru/sitemap.xml"))
    locs = re.findall(r"<loc>(.*?)</loc>", sm_body or "")
    http_locs = [u for u in locs if u.startswith("http://")]
    https_locs = [u for u in locs if u.startswith("https://")]
    ok("main_sitemap", sm_code == 200 and bool(locs), f"HTTP {sm_code}, url={len(locs)}")
    ok(
        "sitemap_https",
        sm_code == 200 and not http_locs and bool(https_locs),
        f"https={len(https_locs)} http={len(http_locs)}"
        + ("" if not http_locs else " — переопубликовать Tilda / поправить SEO"),
    )

    # robots sitemap scheme
    _, _, robots = http_get(main.get("robots", "https://mkekspert.ru/robots.txt"))
    sm_line = next((ln for ln in robots.splitlines() if ln.lower().startswith("sitemap:")), "")
    ok(
        "robots_sitemap_https",
        "https://" in sm_line.lower(),
        sm_line or "нет строки Sitemap",
    )

    # blog
    b_code, _, b_html = http_get(blog.get("host", "https://blog.mkekspert.ru/"))
    ok("blog_reachable", b_code == 200, f"HTTP {b_code}")
    ok("metrika_on_blog", "mc.yandex" in b_html.lower() or "ym(" in b_html, "Метрика на blog")
    bsm_code, _, bsm = http_get(blog.get("sitemap", "https://blog.mkekspert.ru/sitemap.xml"))
    blog_locs = re.findall(r"<loc>(.*?)</loc>", bsm or "")
    ok("blog_sitemap", bsm_code == 200 and len(blog_locs) >= 2, f"статей/url≈{len(blog_locs)}")

    feed_code, _, _ = http_get(blog.get("feed", "https://blog.mkekspert.ru/dzen-feed.xml"))
    ok("dzen_feed", feed_code == 200, f"HTTP {feed_code}")

    # /blog on main
    blog_path_code, blog_path_final, _ = http_get("https://mkekspert.ru/blog")
    ok(
        "main_blog_path",
        blog_path_code in (301, 302) or "blog.mkekspert.ru" in blog_path_final,
        f"HTTP {blog_path_code} → {blog_path_final} (сейчас часто 404 — лучше редирект на blog.*)",
    )

    # razbor
    r_code, _, r_html = http_get(main.get("primary_cta", "https://mkekspert.ru/razbor-direct"))
    ok("cta_razbor", r_code == 200 and bool(re.search(r"<h1", r_html, re.I)), f"HTTP {r_code}")

    print("=== SEO audit mkekspert ===\n")
    failed = 0
    for name, passed, detail in checks:
        mark = "OK  " if passed else "FAIL"
        if not passed:
            failed += 1
        print(f"  [{mark}] {name}: {detail}")

    print()
    if failed:
        print(f"Итог: {failed} проблем(ы). Чеклист: checklists/seo-stack.md")
        return 1
    print("Итог: базовый стек готов к масштабированию статей.")
    return 0


# --- keywords --------------------------------------------------------------


def cmd_keywords_list(_args: argparse.Namespace) -> int:
    data = read_yaml(KEYWORDS_PATH)
    rows = data.get("keywords") or []
    print(f"Ключей: {len(rows)} (обновлено {data.get('updated', '—')})\n")
    print(f"{'status':<12} {'pillar':<4} {'query':<42} url")
    print("-" * 100)
    for row in rows:
        print(
            f"{str(row.get('status', '')):<12} "
            f"{str(row.get('pillar', '')):<4} "
            f"{str(row.get('query', ''))[:42]:<42} "
            f"{row.get('url') or '—'}"
        )
    return 0


def cmd_keywords_add(args: argparse.Namespace) -> int:
    data = read_yaml(KEYWORDS_PATH)
    rows: list[dict[str, Any]] = list(data.get("keywords") or [])
    q = args.query.strip()
    kid = args.id or slugify(q)
    if any(r.get("id") == kid or r.get("query") == q for r in rows):
        print(f"Уже есть id/query: {kid}")
        return 1
    rows.append(
        {
            "id": kid,
            "query": q,
            "pillar": args.pillar or "P1",
            "intent": args.intent or "info",
            "status": args.status or "idea",
            "url": args.url or "",
            "lsi": [],
            "campaign_id": kid,
        }
    )
    data["keywords"] = rows
    data["updated"] = dt.date.today().isoformat()
    write_yaml(KEYWORDS_PATH, data)
    print(f"Добавлен: {kid} — {q}")
    return 0


# --- positions -------------------------------------------------------------


def _today_stamp() -> str:
    return dt.date.today().isoformat()


def cmd_positions_record(args: argparse.Namespace) -> int:
    POSITIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = POSITIONS_DIR / f"{_today_stamp()}.yaml"
    data = read_yaml(path) if path.exists() else {
        "date": _today_stamp(),
        "engine": args.engine or "yandex",
        "region": args.region,
        "device": "desktop",
        "notes": "ручная запись",
        "results": [],
    }
    results: list[dict[str, Any]] = list(data.get("results") or [])
    q = args.query.strip()
    results = [r for r in results if r.get("query") != q]
    results.append(
        {
            "query": q,
            "position": args.pos,
            "url_found": args.url_found or "",
        }
    )
    data["results"] = results
    write_yaml(path, data)
    print(f"Записано в {path.relative_to(ROOT)}: «{q}» → {args.pos}")
    return 0


def cmd_positions_import(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.is_absolute():
        src = (Path.cwd() / src).resolve()
    if not src.exists():
        # try relative to SEO_DIR
        alt = (SEO_DIR / args.file).resolve()
        src = alt if alt.exists() else src
    if not src.exists():
        print(f"Файл не найден: {args.file}")
        return 1
    data = read_yaml(src)
    date = str(data.get("date") or _today_stamp())
    dest = POSITIONS_DIR / f"{date}.yaml"
    write_yaml(dest, data)
    n = len(data.get("results") or [])
    print(f"Импорт {n} строк → {dest.relative_to(ROOT)}")
    return 0


def cmd_positions_fetch(_args: argparse.Namespace) -> int:
    load_dotenv_local()
    provider = (os.getenv("SEO_SERP_PROVIDER") or "").strip().lower()
    if not provider:
        print(
            "SEO_SERP_PROVIDER не задан — автосъём выключен.\n"
            "Заполните seo/positions/manual-input.example.yaml и:\n"
            "  python3 seo_pipeline.py positions import ../seo/positions/<date>.yaml"
        )
        return 2

    if provider != "xmlriver":
        print(f"Провайдер «{provider}» пока не поддержан (есть: xmlriver).")
        return 1

    user = os.getenv("SEO_SERP_USER") or ""
    key = os.getenv("SEO_SERP_KEY") or ""
    if not user or not key:
        print("Нужны SEO_SERP_USER и SEO_SERP_KEY в .env")
        return 1

    kw = read_yaml(KEYWORDS_PATH).get("keywords") or []
    queries = [r["query"] for r in kw if r.get("query") and r.get("status") != "idea"]
    results: list[dict[str, Any]] = []
    for q in queries:
        pos, found = _xmlriver_yandex(user, key, q)
        results.append({"query": q, "position": pos, "url_found": found or ""})
        print(f"  {pos or '—':>4}  {q}")

    data = {
        "date": _today_stamp(),
        "engine": "yandex",
        "region": os.getenv("SEO_SERP_REGION", "213"),
        "device": "desktop",
        "notes": "xmlriver fetch",
        "results": results,
    }
    dest = POSITIONS_DIR / f"{_today_stamp()}.yaml"
    write_yaml(dest, data)
    print(f"\nСнимок: {dest.relative_to(ROOT)}")
    return 0


def _xmlriver_yandex(user: str, key: str, query: str) -> tuple[int | None, str | None]:
    """Minimal XMLRiver Yandex search. Docs: https://xmlriver.com/"""
    from urllib.parse import urlencode

    params = urlencode(
        {
            "user": user,
            "key": key,
            "query": query,
            "groupby": 10,
            "page": 0,
            "lr": os.getenv("SEO_SERP_REGION", "213"),
            "device": "desktop",
        }
    )
    url = f"http://xmlriver.com/search_yandex/xml?{params}"
    code, _, body = http_get(url, timeout=60)
    if code != 200 or not body.strip().startswith("<"):
        return None, None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None, None
    # typical path: response/results/grouping/group/doc
    hosts = ("blog.mkekspert.ru", "mkekspert.ru")
    rank = 0
    for doc in root.iter("doc"):
        rank += 1
        url_el = doc.find("url")
        u = (url_el.text or "") if url_el is not None else ""
        if any(h in u for h in hosts):
            return rank, u
    # if nothing ours — still return None (out of top groups fetched)
    return None, None


# --- report / status -------------------------------------------------------


def _latest_positions() -> dict[str, Any] | None:
    if not POSITIONS_DIR.exists():
        return None
    files = sorted(
        [p for p in POSITIONS_DIR.glob("*.yaml") if "example" not in p.name],
        reverse=True,
    )
    if not files:
        return None
    return read_yaml(files[0])


def cmd_report(_args: argparse.Namespace) -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    kw_data = read_yaml(KEYWORDS_PATH)
    keywords = kw_data.get("keywords") or []
    snap = _latest_positions()
    by_q = {}
    if snap:
        for r in snap.get("results") or []:
            by_q[r.get("query")] = r

    lines = [
        f"# SEO report — {dt.date.today().isoformat()}",
        "",
        f"Ключей в банке: **{len(keywords)}**",
        f"Последний замер: **{(snap or {}).get('date', 'нет')}**",
        "",
        "## Воронка статусов",
        "",
    ]
    from collections import Counter

    c = Counter(str(k.get("status") or "?") for k in keywords)
    for st, n in sorted(c.items()):
        lines.append(f"- `{st}`: {n}")

    lines += ["", "## Позиции (наш домен в выдаче)", "", "| Запрос | Поз. | URL | Статус ключа |", "|---|---:|---|---|"]
    for k in keywords:
        q = k.get("query")
        r = by_q.get(q) or {}
        pos = r.get("position")
        pos_s = "—" if pos is None else str(pos)
        lines.append(
            f"| {q} | {pos_s} | {r.get('url_found') or k.get('url') or '—'} | {k.get('status')} |"
        )

    # audit embed
    lines += ["", "## Аудит (кратко)", "", "```"]
    # capture audit by calling checks lightly
    old_argv = sys.argv
    try:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_audit(argparse.Namespace())
        lines.append(buf.getvalue().rstrip())
    finally:
        sys.argv = old_argv
    lines.append("```")
    lines += [
        "",
        "## Следующие шаги",
        "",
        "1. Закрыть FAIL из аудита (`checklists/seo-stack.md`)",
        "2. Ключи `idea` → бриф → статья",
        "3. Позиции 11–30 → усилить текст / внутренние ссылки",
        "4. Повторить замер через неделю",
        "",
    ]

    text = "\n".join(lines) + "\n"
    out = REPORTS_DIR / f"{dt.date.today().isoformat()}.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Сохранено: {out.relative_to(ROOT)}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    kw = read_yaml(KEYWORDS_PATH).get("keywords") or []
    from collections import Counter

    c = Counter(str(k.get("status") or "?") for k in kw)
    print("=== SEO pipeline status ===\n")
    print(f"Банк ключей: {KEYWORDS_PATH.relative_to(ROOT)}")
    for st in ("idea", "brief", "draft", "published", "indexed", "tracking", "top10", "top3", "refresh"):
        if c.get(st):
            print(f"  {st:<12} {c[st]}")
    other = {k: v for k, v in c.items() if k not in {
        "idea", "brief", "draft", "published", "indexed", "tracking", "top10", "top3", "refresh"
    }}
    for st, n in other.items():
        print(f"  {st:<12} {n}")

    snap = _latest_positions()
    print(f"\nПозиции: {(snap or {}).get('date', 'нет замеров')}")
    ideas = [k for k in kw if k.get("status") == "idea"]
    if ideas:
        print("\nОчередь idea (писать дальше):")
        for k in ideas[:10]:
            print(f"  - [{k.get('pillar')}] {k.get('query')}  id={k.get('id')}")
    print("\nДокумент: docs/seo-pipeline.md")
    return 0


def main() -> int:
    load_dotenv_local()
    parser = argparse.ArgumentParser(description="SEO-пайплайн mkekspert")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("audit", help="Живой аудит Tilda + blog")
    sub.add_parser("status", help="Воронка ключей и очередь")
    sub.add_parser("report", help="Недельный отчёт + аудит")

    kw = sub.add_parser("keywords", help="Банк ключей")
    kws = kw.add_subparsers(dest="keywords_cmd", required=True)
    kws.add_parser("list")
    ka = kws.add_parser("add")
    ka.add_argument("--query", required=True)
    ka.add_argument("--id")
    ka.add_argument("--url", default="")
    ka.add_argument("--pillar", default="P1")
    ka.add_argument("--intent", default="info")
    ka.add_argument("--status", default="idea")

    pos = sub.add_parser("positions", help="Съём / запись позиций")
    poss = pos.add_subparsers(dest="positions_cmd", required=True)
    pr = poss.add_parser("record", help="Одна позиция вручную")
    pr.add_argument("--query", required=True)
    pr.add_argument("--pos", type=int, required=True)
    pr.add_argument("--url-found", default="")
    pr.add_argument("--engine", default="yandex")
    pr.add_argument("--region", default="213")
    pi = poss.add_parser("import", help="Импорт YAML замера")
    pi.add_argument("file")
    poss.add_parser("fetch", help="Автосъём (нужен SEO_SERP_*)")

    args = parser.parse_args()
    if args.command == "audit":
        return cmd_audit(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "keywords":
        if args.keywords_cmd == "list":
            return cmd_keywords_list(args)
        if args.keywords_cmd == "add":
            return cmd_keywords_add(args)
    if args.command == "positions":
        if args.positions_cmd == "record":
            return cmd_positions_record(args)
        if args.positions_cmd == "import":
            return cmd_positions_import(args)
        if args.positions_cmd == "fetch":
            return cmd_positions_fetch(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
