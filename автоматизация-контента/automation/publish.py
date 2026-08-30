#!/usr/bin/env python3
"""
Публикация mkekspert: 4 потока контента.

  dzen/articles  → TELEGRAM_DZEN_CHANNEL → @zen_sync_bot → Дзен
  dzen/teasers/tg → TELEGRAM_MAIN_CHANNEL (@mariyaprodirect)
  dzen/teasers/vk → VK
  articles/tg, articles/vk → отдельные команды

Примеры:
  python publish.py queue list
  python publish.py queue approve 7-errors-direct
  python publish.py publish dzen 7-errors-direct --dry-run
  python publish.py publish teasers 7-errors-direct
  python publish.py publish tg-post my-post-id
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "queue" / "publish-queue.yaml"
ENV_FILE = Path(__file__).resolve().parent / ".env"

TG_CAPTION_LIMIT = 1024
TG_MESSAGE_LIMIT = 4096
DZEN_TITLE_LIMIT = 140


@dataclass
class Article:
    title: str
    body: str
    utm_campaign: str
    source_path: Path


@dataclass
class PublishResult:
    platform: str
    ok: bool
    message: str
    message_id: int | None = None


def load_env() -> None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name, str(default)).lower()
    return val in ("1", "true", "yes", "on")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].lstrip("\n")


def markdown_to_plain(md: str) -> str:
    lines: list[str] = []
    for line in md.splitlines():
        if line.strip() == "---":
            continue
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_plain_post(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    return markdown_to_plain(body) if meta or body.startswith("#") else raw.strip()


def load_article(path: Path) -> Article:
    raw = path.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(raw)
    title = str(meta.get("h1") or meta.get("title") or "").strip()
    if not title:
        raise ValueError(f"Нет title/h1 в {path}")
    body = markdown_to_plain(body_md)
    if body.startswith(title):
        body = body[len(title) :].lstrip("\n")
    utm = str(meta.get("utm_campaign") or "article")
    return Article(title=title, body=body, utm_campaign=utm, source_path=path)


def format_for_dzen(article: Article) -> str:
    title = article.title.strip()
    if not title.endswith((".", "!", "?", "…")):
        title = title + "."
    if len(title) > DZEN_TITLE_LIMIT:
        raise ValueError(f"Заголовок {len(title)} символов — лимит Дзена {DZEN_TITLE_LIMIT}.")
    return f"{title}\n\n{article.body}"


def load_queue() -> list[dict[str, Any]]:
    if not QUEUE_FILE.exists():
        return []
    data = yaml.safe_load(QUEUE_FILE.read_text(encoding="utf-8")) or {}
    return data.get("items", [])


def save_queue(items: list[dict[str, Any]]) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(
        yaml.dump({"items": items}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def find_queue_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def resolve_path(rel: str) -> Path:
    p = ROOT / rel
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def article_path(item: dict[str, Any]) -> str:
    """Поддержка старого ключа article и нового dzen_article."""
    return str(item.get("dzen_article") or item.get("article", ""))


def teaser_tg_path(item: dict[str, Any]) -> str | None:
    return item.get("dzen_teaser_tg") or item.get("teaser")


def teaser_vk_path(item: dict[str, Any]) -> str | None:
    return item.get("dzen_teaser_vk") or item.get("vk_post")


def replace_dzen_url(text: str, url: str) -> str:
    return text.replace("[ссылка]", url or "[ссылка на Дзен]")


def telegram_api(method: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    resp = requests.post(url, json=payload, timeout=60)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API {method}: {data.get('description', data)}")
    return data


def publish_telegram(
    text: str,
    channel_id: str,
    token: str,
    *,
    cover: Path | None = None,
    dry_run: bool = False,
) -> PublishResult:
    if len(text) > TG_MESSAGE_LIMIT:
        raise ValueError(f"Текст {len(text)} символов — лимит Telegram {TG_MESSAGE_LIMIT}.")

    if dry_run:
        mode = "фото+текст" if cover and len(text) <= TG_CAPTION_LIMIT else "текст"
        preview = text[:400] + ("…" if len(text) > 400 else "")
        return PublishResult("telegram", True, f"[dry-run] → {channel_id} ({mode})\n{preview}")

    if cover and cover.exists() and len(text) <= TG_CAPTION_LIMIT:
        with cover.open("rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": channel_id, "caption": text},
                files={"photo": f},
                timeout=120,
            )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", data))
        return PublishResult("telegram", True, "Фото + текст", data["result"]["message_id"])

    if cover and cover.exists() and len(text) > TG_CAPTION_LIMIT:
        print("⚠ Текст >1024 — обложка в Дзен-Студии вручную или сократите тизер.", file=sys.stderr)

    data = telegram_api(
        "sendMessage",
        {"chat_id": channel_id, "text": text, "disable_web_page_preview": False},
        token,
    )
    return PublishResult("telegram", True, "Текст опубликован", data["result"]["message_id"])


def publish_vk(text: str, token: str, group_id: str, *, dry_run: bool = False) -> PublishResult:
    if dry_run:
        return PublishResult("vk", True, f"[dry-run] → группа {group_id}")
    resp = requests.post(
        "https://api.vk.com/method/wall.post",
        data={
            "access_token": token,
            "v": "5.199",
            "owner_id": f"-{group_id}",
            "from_group": 1,
            "message": text,
        },
        timeout=60,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API: {data['error']}")
    return PublishResult("vk", True, f"Пост #{data['response']['post_id']}", data["response"]["post_id"])


def require_approved(item: dict[str, Any], force: bool) -> None:
    if item.get("status") != "approved" and not force:
        raise SystemExit(
            f"Статус «{item.get('status')}». Сначала: python publish.py queue approve {item['id']}"
        )


def publish_dzen_article(
    item: dict[str, Any], *, dry_run: bool, token: str, channel: str
) -> None:
    path = article_path(item)
    if not path:
        raise SystemExit("В очереди нет dzen_article")
    article = load_article(resolve_path(path))
    text = format_for_dzen(article)
    cover = None
    if item.get("cover"):
        cover = ROOT / item["cover"]
    r = publish_telegram(text, channel, token, cover=cover, dry_run=dry_run)
    print(f"DZEN-канал ({channel}): {r.message}")
    if not dry_run:
        print("  → Синхробот подхватит в Дзен за 2–10 мин")


def publish_dzen_teasers(
    item: dict[str, Any], *, dry_run: bool, token: str, main_ch: str, vk_token: str, vk_group: str
) -> None:
    url = item.get("dzen_url", "")
    if not url and not dry_run:
        print("⚠ dzen_url пустой — вставьте ссылку на статью в очередь", file=sys.stderr)

    cover = ROOT / item["cover"] if item.get("cover") else None

    tg_path = teaser_tg_path(item)
    if tg_path and main_ch:
        text = replace_dzen_url(load_plain_post(resolve_path(tg_path)), url)
        r = publish_telegram(text, main_ch, token, cover=cover, dry_run=dry_run)
        print(f"TG тизер ({main_ch}): {r.message}")

    vk_path = teaser_vk_path(item)
    if vk_path and vk_token and vk_group:
        text = replace_dzen_url(load_plain_post(resolve_path(vk_path)), url)
        r = publish_vk(text, vk_token, vk_group, dry_run=dry_run)
        print(f"VK тизер: {r.message}")
    elif vk_path and not dry_run:
        print("ℹ VK: задайте VK_ACCESS_TOKEN и VK_GROUP_ID в .env")


def publish_standalone_tg(post_id: str, *, dry_run: bool, force: bool) -> int:
    items = load_queue()
    item = find_queue_item(items, post_id)
    if item and item.get("tg_post"):
        require_approved(item, force)
        path = item["tg_post"]
    else:
        path = f"articles/tg/{post_id}.md"
    text = load_plain_post(resolve_path(path))
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    ch = os.environ["TELEGRAM_MAIN_CHANNEL_ID"]
    r = publish_telegram(text, ch, token, dry_run=dry_run)
    print(f"TG пост ({ch}): {r.message}")
    return 0


def publish_standalone_vk(post_id: str, *, dry_run: bool, force: bool) -> int:
    items = load_queue()
    item = find_queue_item(items, post_id)
    if item and item.get("vk_post") and not item.get("dzen_teaser_vk"):
        require_approved(item, force)
        path = item["vk_post"]
    else:
        path = f"articles/vk/{post_id}.md"
    text = load_plain_post(resolve_path(path))
    r = publish_vk(text, os.environ["VK_ACCESS_TOKEN"], os.environ["VK_GROUP_ID"], dry_run=dry_run)
    print(f"VK пост: {r.message}")
    return 0


def cmd_publish(target: str, item_id: str, *, dry_run: bool, force: bool) -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    dzen_ch = os.getenv("TELEGRAM_DZEN_CHANNEL_ID", "")
    main_ch = os.getenv("TELEGRAM_MAIN_CHANNEL_ID", "")
    vk_token = os.getenv("VK_ACCESS_TOKEN", "")
    vk_group = os.getenv("VK_GROUP_ID", "")

    if target == "tg-post":
        return publish_standalone_tg(item_id, dry_run=dry_run, force=force)
    if target == "vk-post":
        return publish_standalone_vk(item_id, dry_run=dry_run, force=force)

    items = load_queue()
    item = find_queue_item(items, item_id)
    if not item:
        raise SystemExit(f"Нет записи {item_id} в очереди")

    if target in ("dzen", "all"):
        require_approved(item, force)
        if dzen_ch == main_ch and dzen_ch:
            raise SystemExit(
                "TELEGRAM_DZEN_CHANNEL_ID и TELEGRAM_MAIN_CHANNEL_ID совпадают — "
                "разделите каналы. См. docs/content-channels.md"
            )
        if not token or not dzen_ch:
            raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_DZEN_CHANNEL_ID")
        publish_dzen_article(item, dry_run=dry_run, token=token, channel=dzen_ch)

    if target in ("teasers", "all"):
        if target == "teasers":
            require_approved(item, force)
        if not token or not main_ch:
            raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_MAIN_CHANNEL_ID")
        publish_dzen_teasers(
            item, dry_run=dry_run, token=token, main_ch=main_ch,
            vk_token=vk_token, vk_group=vk_group,
        )

    if target == "all" and not dry_run:
        item["status"] = "published"
        item["published_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(items)

    if dry_run:
        print("\n[dry-run] Для реальной публикации: DRY_RUN=false python publish.py publish", target, item_id)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Публикация контента mkekspert")
    sub = parser.add_subparsers(dest="command", required=True)

    q = sub.add_parser("queue")
    qs = q.add_subparsers(dest="queue_cmd", required=True)
    qs.add_parser("list")
    ap = qs.add_parser("approve")
    ap.add_argument("id")

    pub = sub.add_parser("publish")
    pub.add_argument(
        "target",
        choices=["dzen", "teasers", "all", "tg-post", "vk-post"],
        help="dzen=статья в DZEN-канал; teasers=тизеры в TG+VK; all=всё",
    )
    pub.add_argument("id")
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--force", action="store_true")

    fmt = sub.add_parser("format")
    fmt.add_argument("article", help="путь от автоматизация-контента/")

    args = parser.parse_args()

    if args.command == "queue":
        if args.queue_cmd == "list":
            for item in load_queue():
                print(
                    f"- {item['id']}: {item.get('status', '?')} | "
                    f"dzen: {article_path(item) or '—'}"
                )
            return 0
        if args.queue_cmd == "approve":
            items = load_queue()
            item = find_queue_item(items, args.id)
            if not item:
                return 1
            item["status"] = "approved"
            item["approved_at"] = datetime.now(timezone.utc).isoformat()
            save_queue(items)
            print(f"✓ {args.id} → approved")
            return 0

    if args.command == "format":
        article = load_article(resolve_path(args.article))
        text = format_for_dzen(article)
        print(text)
        print(f"\n--- {len(text)} символов ---")
        return 0

    if args.command == "publish":
        dry = True if args.dry_run else env_bool("DRY_RUN", True)
        return cmd_publish(args.target, args.id, dry_run=dry, force=args.force)

    return 0


if __name__ == "__main__":
    load_env()
    sys.exit(main())
