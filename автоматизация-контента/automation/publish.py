#!/usr/bin/env python3
"""
Публикация контента mkekspert: Telegram → Дзен (через zen_sync_bot), VK.

Дзен не имеет публичного API. Официальный путь — пост в TG-канале,
привязанном к @zen_sync_bot (Синхробот Дзена).

Использование:
  python publish.py queue list
  python publish.py queue approve 7-errors-direct
  python publish.py publish 7-errors-direct --dry-run
  python publish.py publish 7-errors-direct
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


def load_article(path: Path) -> Article:
    raw = path.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(raw)
    title = str(meta.get("h1") or meta.get("title") or "").strip()
    if not title:
        raise ValueError(f"Нет title/h1 в {path}")
    body = markdown_to_plain(body_md)
  # убрать дубль заголовка в начале тела
    if body.startswith(title):
        body = body[len(title) :].lstrip("\n")
    utm = str(meta.get("utm_campaign") or "article")
    return Article(title=title, body=body, utm_campaign=utm, source_path=path)


def format_for_dzen(article: Article) -> str:
    """Первое предложение = заголовок в Дзене (до 140 символов)."""
    title = article.title.strip()
    if not title.endswith((".", "!", "?", "…")):
        title = title + "."
    if len(title) > DZEN_TITLE_LIMIT:
        raise ValueError(
            f"Заголовок {len(title)} символов — лимит Дзена {DZEN_TITLE_LIMIT}. "
            "Сократите title/h1 в frontmatter."
        )
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
        raise ValueError(
            f"Текст {len(text)} символов — лимит Telegram {TG_MESSAGE_LIMIT}. "
            "Разбейте статью или сократите."
        )

    if dry_run:
        mode = "фото+текст" if cover and len(text) <= TG_CAPTION_LIMIT else (
            "фото (заголовок) + текст" if cover else "текст"
        )
        preview = text[:500] + ("…" if len(text) > 500 else "")
        return PublishResult(
            platform="telegram",
            ok=True,
            message=f"[dry-run] → {channel_id} ({mode})\n{preview}",
        )

    if cover and cover.exists():
        if len(text) <= TG_CAPTION_LIMIT:
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
            return PublishResult("telegram", True, "Фото + полный текст (→Дзен с обложкой)", data["result"]["message_id"])

        # длинная статья: обложка отдельно не склеится с текстом в один пост Дзена
        title_line = text.split("\n", 1)[0]
        with cover.open("rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": channel_id, "caption": title_line},
                files={"photo": f},
                timeout=120,
            )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", data))
        print(
            "⚠ Статья длинная — обложку добавьте в Студии Дзена после синхронизации.",
            file=sys.stderr,
        )

    data = telegram_api(
        "sendMessage",
        {"chat_id": channel_id, "text": text, "disable_web_page_preview": False},
        token,
    )
    mid = data["result"]["message_id"]
    return PublishResult("telegram", True, "Текст опубликован", mid)


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
    post_id = data["response"]["post_id"]
    return PublishResult("vk", True, f"Пост #{post_id}", post_id)


def cmd_queue_list(_: argparse.Namespace) -> int:
    items = load_queue()
    if not items:
        print("Очередь пуста.")
        return 0
    for item in items:
        print(
            f"- {item['id']}: {item.get('status', '?')} "
            f"| dzen: {item.get('article', '—')} "
            f"| teaser: {item.get('teaser', '—')}"
        )
    return 0


def cmd_queue_approve(args: argparse.Namespace) -> int:
    items = load_queue()
    item = find_queue_item(items, args.id)
    if not item:
        print(f"Нет записи {args.id}", file=sys.stderr)
        return 1
    item["status"] = "approved"
    item["approved_at"] = datetime.now(timezone.utc).isoformat()
    save_queue(items)
    print(f"✓ {args.id} → approved")
    return 0


def publish_item(item_id: str, *, dry_run: bool | None = None, force: bool = False) -> int:
    load_env()
    if dry_run is None:
        dry_run = env_bool("DRY_RUN", True)

    items = load_queue()
    item = find_queue_item(items, item_id)
    if not item:
        print(f"Нет записи {item_id} в очереди", file=sys.stderr)
        return 1

    if item.get("status") != "approved" and not force:
        print(
            f"Статус «{item.get('status')}». Сначала: python publish.py queue approve {item_id}",
            file=sys.stderr,
        )
        return 1

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    dzen_channel = os.getenv("TELEGRAM_DZEN_CHANNEL_ID", "")
    teaser_channel = os.getenv("TELEGRAM_TEASER_CHANNEL_ID", "") or dzen_channel
    vk_token = os.getenv("VK_ACCESS_TOKEN", "")
    vk_group = os.getenv("VK_GROUP_ID", "")

    results: list[PublishResult] = []

    # 1. Статья → TG (→ Дзен через zen_sync_bot)
    article_path = resolve_path(item["article"])
    article = load_article(article_path)
    dzen_text = format_for_dzen(article)
    cover_path = Path(item["cover"]) if item.get("cover") else None
    if cover_path and not cover_path.is_absolute():
        cover_path = ROOT / cover_path

    if not token or not dzen_channel:
        if dry_run:
            print("[dry-run] TELEGRAM_BOT_TOKEN / TELEGRAM_DZEN_CHANNEL_ID не заданы")
            print("--- Текст для Дзен (первые 800 символов) ---")
            print(dzen_text[:800])
        else:
            print("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_DZEN_CHANNEL_ID в .env", file=sys.stderr)
            return 1
    else:
        r = publish_telegram(
            dzen_text,
            dzen_channel,
            token,
            cover=cover_path,
            dry_run=dry_run,
        )
        results.append(r)
        print(f"TG (→Дзен): {r.message}")

    # 2. Тизер в TG (отдельный канал или тот же)
    if item.get("teaser"):
        teaser_path = resolve_path(item["teaser"])
        teaser_text = teaser_path.read_text(encoding="utf-8").strip()
        teaser_text = teaser_text.replace("[ссылка]", item.get("dzen_url", "[ссылка на Дзен]"))

        if item.get("teaser_channel") != "dzen" and teaser_channel != dzen_channel:
            if token:
                r = publish_telegram(teaser_text, teaser_channel, token, dry_run=dry_run)
                results.append(r)
                print(f"TG тизер: {r.message}")
        elif not dry_run:
            print("ℹ Тизер не публикуется в тот же канал, что и статья (чтобы не дублировать в Дзен).")
            print("  Задайте TELEGRAM_TEASER_CHANNEL_ID или публикуйте тизер вручную после появления ссылки.")

    # 3. VK
    if item.get("vk_post") and vk_token and vk_group:
        vk_path = resolve_path(item["vk_post"])
        vk_text = vk_path.read_text(encoding="utf-8").strip()
        vk_text = vk_text.replace("[ссылка]", item.get("dzen_url", "[ссылка]"))
        r = publish_vk(vk_text, vk_token, vk_group, dry_run=dry_run)
        results.append(r)
        print(f"VK: {r.message}")
    elif item.get("vk_post") and not dry_run:
        print("ℹ VK: задайте VK_ACCESS_TOKEN и VK_GROUP_ID в .env")

    if not dry_run:
        item["status"] = "published"
        item["published_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(items)
        print(f"\n✓ {item_id} опубликовано. Дзен подхватит за 2–10 мин (zen_sync_bot).")
        print("  Проверьте Студию: https://dzen.ru/studio")
    else:
        print("\n[dry-run] Для реальной публикации: DRY_RUN=false python publish.py publish", item_id)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Публикация контента mkekspert")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("queue", help="Очередь")
    qsub = p_list.add_subparsers(dest="queue_cmd", required=True)
    qsub.add_parser("list", help="Список")
    p_app = qsub.add_parser("approve", help="Согласовать")
    p_app.add_argument("id")

    p_pub = sub.add_parser("publish", help="Опубликовать")
    p_pub.add_argument("id")
    p_pub.add_argument("--dry-run", action="store_true")
    p_pub.add_argument("--force", action="store_true", help="Без статуса approved")

    p_fmt = sub.add_parser("format", help="Показать текст для Дзен")
    p_fmt.add_argument("article", help="Путь к md относительно автоматизация-контента/")

    args = parser.parse_args()

    if args.command == "queue":
        if args.queue_cmd == "list":
            return cmd_queue_list(args)
        if args.queue_cmd == "approve":
            return cmd_queue_approve(args)

    if args.command == "format":
        article = load_article(resolve_path(args.article))
        print(format_for_dzen(article))
        print(f"\n--- {len(format_for_dzen(article))} символов ---")
        return 0

    if args.command == "publish":
        dry = True if args.dry_run else env_bool("DRY_RUN", True)
        return publish_item(args.id, dry_run=dry, force=args.force)

    return 0


if __name__ == "__main__":
    load_env()
    sys.exit(main())
