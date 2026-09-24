#!/usr/bin/env python3
"""Пайплайн обложек: облако готовит бриф → Codex на ПК рисует → облако забирает файлы.

  python3 covers_pipeline.py request <id> [--vk-post-id N]
  python3 covers_pipeline.py status
  python3 covers_pipeline.py pickup [--deploy]
  python3 covers_pipeline.py brief <id>   # только пересобрать briefs/covers/<id>.md
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "queue" / "covers-inbox.yaml"
BRIEFS = ROOT / "briefs" / "covers"
COVERS = ROOT / "assets" / "covers"
PUBLISH_Q = ROOT / "queue" / "publish-queue.yaml"
POSTS_Q = ROOT / "queue" / "posts-queue.yaml"
STYLE_REF = "assets/covers/_import/style-ref.png"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_inbox() -> list[dict[str, Any]]:
    data = load_yaml(INBOX)
    items = data.get("items") if isinstance(data, dict) else data
    return list(items or [])


def save_inbox(items: list[dict[str, Any]]) -> None:
    save_yaml(INBOX, {"items": items})


def find_content(item_id: str) -> dict[str, Any]:
    for path in (PUBLISH_Q, POSTS_Q):
        raw = load_yaml(path)
        rows = raw.get("items") if isinstance(raw, dict) else raw
        for row in rows or []:
            if row.get("id") == item_id:
                return dict(row)
    raise SystemExit(f"id «{item_id}» нет в publish-queue / posts-queue")


def slug_of(item: dict[str, Any]) -> str:
    cover = item.get("cover") or ""
    if cover:
        return Path(cover).stem.replace("-vk", "")
    return str(item["id"])


def headline_of(item: dict[str, Any]) -> str:
    return (
        item.get("cover_headline")
        or item.get("topic")
        or item.get("title")
        or item["id"]
    )


def subline_of(item: dict[str, Any]) -> str:
    return item.get("cover_subline") or item.get("platform") or "mkekspert"


def platforms_of(item: dict[str, Any]) -> list[str]:
    plat = item.get("platform")
    if plat == "vk":
        return ["vk"]
    if plat == "tg":
        return ["tg"]
    # campaigns → dzen + teasers
    return ["dzen", "tg", "vk"]


def write_brief(item: dict[str, Any], *, vk_post_id: int | None = None) -> Path:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    slug = slug_of(item)
    headline = headline_of(item)
    subline = subline_of(item)
    plats = platforms_of(item)
    out_l = f"assets/covers/{slug}.jpg"
    out_vk = f"assets/covers/{slug}-vk.jpg"
    path = BRIEFS / f"{slug}.md"

    need_l = "dzen" in plats or "tg" in plats
    need_vk = "vk" in plats

    lines = [
        f"# Codex brief: обложка `{slug}`",
        "",
        "Сделай **файлы в этом репозитории** (не только превью в чате).",
        "Если JPG уже лежит в `assets/covers/` — **перезапиши** новой качественной версией.",
        "Стиль: claymorphism / soft 3D, ivory `#FDFBF7`, акценты терракота / изумруд / золото.",
        f"Референс стиля (не копировать объект 1-в-1): `{STYLE_REF}`",
        "",
        "## Текст на обложке",
        f"- Заголовок: **{headline}**",
        f"- Подзаголовок: **{subline}**",
        "- Бренд внизу: `mkekspert.ru`",
        "",
        "## Файлы (обязательно оба пути, если платформа нужна)",
    ]
    if need_l:
        lines += [
            f"1. `{out_l}` — **1200×630** (Дзен / TG)",
        ]
    if need_vk:
        lines += [
            f"{'2' if need_l else '1'}. `{out_vk}` — **1080×1080** (VK, Мария крепит вручную)",
        ]
    lines += [
        "",
        "## Промпт (можно уточнить объект, но не стиль)",
        "",
        "```",
        f"Claymorphism marketing cover for Yandex Direct B2B expert Maria Kovaleva. "
        f"Headline «{headline}», subline «{subline}», brand mkekspert.ru. "
        "Soft ivory background, terracotta/emerald/gold accents, gentle 3D clay shapes, "
        "orbital thin lines, unique central 3D object matching the topic "
        "(not the same phone every time). No badges, no arrows, no «В итоге» card. "
        "High-end editorial, clean typography space for the title.",
        "```",
        "",
        "## Когда готово",
        "",
        "1. Сохрани файлы в `assets/covers/` с именами выше.",
        "2. Закоммить и запушь в ветку агента **или** скажи облачному агенту: "
        "`covers pickup`.",
        "",
    ]
    if vk_post_id:
        lines += [
            f"VK пост для ручной вставки: https://vk.com/wall-222121025_{vk_post_id}",
            "",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def cmd_request(args: argparse.Namespace) -> int:
    item = find_content(args.id)
    slug = slug_of(item)
    brief = write_brief(item, vk_post_id=args.vk_post_id)
    inbox = load_inbox()
    existing = next((x for x in inbox if x.get("id") == args.id or x.get("slug") == slug), None)
    row = {
        "id": args.id,
        "slug": slug,
        "status": "waiting_codex",
        "platforms": platforms_of(item),
        "headline": headline_of(item),
        "subline": subline_of(item),
        "out_landscape": f"assets/covers/{slug}.jpg",
        "out_vk": f"assets/covers/{slug}-vk.jpg",
        "brief": str(brief.relative_to(ROOT)),
        "vk_post_id": args.vk_post_id,
        "requested_at": now_iso(),
    }
    if existing:
        existing.update(row)
        # keep ready_at if any
    else:
        inbox.append(row)
    save_inbox(inbox)
    print(f"✓ inbox ← {args.id} (waiting_codex)")
    print(f"  brief: {brief.relative_to(ROOT)}")
    print("  Codex на ПК: открой brief и сохрани JPG в assets/covers/")
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    item = find_content(args.id)
    path = write_brief(item, vk_post_id=args.vk_post_id)
    print(f"✓ {path.relative_to(ROOT)}")
    return 0


def file_ok(rel: str) -> bool:
    p = ROOT / rel
    return p.exists() and p.stat().st_size > 20_000


def cmd_status(_args: argparse.Namespace) -> int:
    inbox = load_inbox()
    if not inbox:
        print("covers-inbox пуст")
        return 0
    for row in inbox:
        slug = row.get("slug") or row.get("id")
        need = []
        if "dzen" in row.get("platforms", []) or "tg" in row.get("platforms", []):
            need.append(("L", row.get("out_landscape", "")))
        if "vk" in row.get("platforms", []):
            need.append(("VK", row.get("out_vk", "")))
        bits = []
        for label, rel in need:
            bits.append(f"{label}:{'ok' if rel and file_ok(rel) else 'MISS'}")
        print(
            f"{row.get('status'):12} {row.get('id'):20} "
            f"{' '.join(bits)}  brief={row.get('brief','')}"
        )
    return 0


def cmd_pickup(args: argparse.Namespace) -> int:
    inbox = load_inbox()
    changed = 0
    for row in inbox:
        if row.get("status") not in ("waiting_codex", "ready"):
            continue
        plats = row.get("platforms") or []
        ok = True
        missing = []
        if ("dzen" in plats or "tg" in plats) and not file_ok(row.get("out_landscape", "")):
            ok = False
            missing.append(row.get("out_landscape"))
        if "vk" in plats and not file_ok(row.get("out_vk", "")):
            ok = False
            missing.append(row.get("out_vk"))
        if not ok:
            print(f"… {row.get('id')}: ждём {missing}")
            continue
        row["status"] = "ready"
        row["ready_at"] = now_iso()
        changed += 1
        print(f"✓ ready {row.get('id')}")
        if row.get("vk_post_id"):
            print(
                f"  VK вручную: https://vk.com/wall-222121025_{row['vk_post_id']} "
                f"← {row.get('out_vk')}"
            )
            print(f"  или https://blog.mkekspert.ru/covers/{Path(row['out_vk']).name}")
    save_inbox(inbox)

    if args.deploy and changed:
        # deploy covers to blog CDN
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            from dzen_rss import deploy_gh_pages  # type: ignore

            print("deploy gh-pages covers…")
            deploy_gh_pages()
            print("✓ deploy done")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ deploy: {exc}", file=sys.stderr)

    if not changed:
        print("Новых готовых обложек нет")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Cloud ↔ Codex covers pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("request", help="Поставить в inbox + написать brief для Codex")
    r.add_argument("id")
    r.add_argument("--vk-post-id", type=int, default=None)

    b = sub.add_parser("brief", help="Только пересобрать markdown-brief")
    b.add_argument("id")
    b.add_argument("--vk-post-id", type=int, default=None)

    sub.add_parser("status", help="Статус inbox")

    pk = sub.add_parser("pickup", help="Забрать готовые файлы из assets/covers/")
    pk.add_argument(
        "--deploy",
        action="store_true",
        help="После ready — выложить covers на blog.mkekspert.ru",
    )

    args = p.parse_args()
    if args.cmd == "request":
        return cmd_request(args)
    if args.cmd == "brief":
        return cmd_brief(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "pickup":
        return cmd_pickup(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
