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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "queue" / "publish-queue.yaml"
POSTS_QUEUE_FILE = ROOT / "queue" / "posts-queue.yaml"
SCHEDULE_FILE = ROOT / "queue" / "posting-schedule.yaml"
ENV_FILE = Path(__file__).resolve().parent / ".env"
MSK = ZoneInfo("Europe/Moscow")
DZEN_CHANNEL_SLUG = "klientyandtrafik"

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
        line = re.sub(r"__([^_]+)__", r"\1", line)
        line = re.sub(r"~~([^~]+)~~", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdown_to_telegram_html(md: str) -> str:
    """Конвертация **bold**, __italic__, ~~strike~~, `code` для parse_mode=HTML."""
    lines: list[str] = []
    for line in md.splitlines():
        if line.strip() == "---":
            continue
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"__([^_]+)__", r"<i>\1</i>", line)
        line = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", line)
        line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_plain_post(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    return markdown_to_plain(body) if meta or body.startswith("#") else raw.strip()


def load_tg_post(path: Path) -> str:
    """TG-канал: разметка **bold** → HTML."""
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    return markdown_to_telegram_html(body) if meta or body.startswith("#") else markdown_to_telegram_html(raw)


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


def load_posts_queue() -> list[dict[str, Any]]:
    if not POSTS_QUEUE_FILE.exists():
        return []
    data = yaml.safe_load(POSTS_QUEUE_FILE.read_text(encoding="utf-8")) or {}
    return data.get("items", [])


def save_posts_queue(items: list[dict[str, Any]]) -> None:
    POSTS_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    POSTS_QUEUE_FILE.write_text(
        yaml.dump({"items": items}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def find_posts_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


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
    out = text.replace("[ссылка]", url or "[ссылка на Дзен]")
    return out.replace("[ВСТАВЬТЕ ССЫЛКУ НА СТАТЬЮ]", url or "[ссылка на Дзен]")


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
    parse_mode: str = "",
) -> PublishResult:
    if len(text) > TG_MESSAGE_LIMIT:
        raise ValueError(f"Текст {len(text)} символов — лимит Telegram {TG_MESSAGE_LIMIT}.")

    if dry_run:
        mode = "фото+текст" if cover and len(text) <= TG_CAPTION_LIMIT else "текст"
        preview = text[:400] + ("…" if len(text) > 400 else "")
        fmt = f", {parse_mode}" if parse_mode else ""
        return PublishResult("telegram", True, f"[dry-run] → {channel_id} ({mode}{fmt})\n{preview}")

    msg_extra: dict[str, Any] = {}
    if parse_mode:
        msg_extra["parse_mode"] = parse_mode

    if cover and cover.exists() and len(text) <= TG_CAPTION_LIMIT:
        data_payload: dict[str, Any] = {"chat_id": channel_id, "caption": text, **msg_extra}
        with cover.open("rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data=data_payload,
                files={"photo": f},
                timeout=120,
            )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", data))
        return PublishResult("telegram", True, "Фото + текст", data["result"]["message_id"])

    if cover and cover.exists() and len(text) > TG_CAPTION_LIMIT:
        print("⚠ Текст >1024 — фото без подписи, текст отдельным сообщением.", file=sys.stderr)
        with cover.open("rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": channel_id},
                files={"photo": f},
                timeout=120,
            )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", data))

    data = telegram_api(
        "sendMessage",
        {"chat_id": channel_id, "text": text, "disable_web_page_preview": False, **msg_extra},
        token,
    )
    return PublishResult("telegram", True, "Текст опубликован", data["result"]["message_id"])


def vk_api(method: str, token: str, **params: Any) -> dict[str, Any]:
    resp = requests.get(
        f"https://api.vk.com/method/{method}",
        params={"access_token": token, "v": "5.199", **params},
        timeout=60,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API {method}: {data['error']}")
    return data["response"]


def resolve_vk_group_id(token: str, group_id: str) -> int:
    if group_id.lstrip("-").isdigit():
        return int(group_id.lstrip("-"))
    data = vk_api("groups.getById", token, group_id=group_id)
    groups = data.get("groups") or data
    if isinstance(groups, list):
        return int(groups[0]["id"])
    return int(groups["id"])


def upload_vk_wall_photo(user_token: str, group_id: int, image_path: Path) -> str:
    """Загрузка фото на стену — только пользовательский токен (не ключ сообщества)."""
    up_srv = vk_api("photos.getWallUploadServer", user_token, group_id=group_id)
    with image_path.open("rb") as f:
        up = requests.post(up_srv["upload_url"], files={"photo": f}, timeout=120).json()
    saved = vk_api(
        "photos.saveWallPhoto",
        user_token,
        group_id=group_id,
        photo=up["photo"],
        server=up["server"],
        hash=up["hash"],
    )
    ph = saved[0]
    return f"photo{ph['owner_id']}_{ph['id']}"


def publish_vk(
    text: str,
    token: str,
    group_id: str,
    *,
    cover: Path | None = None,
    user_token: str = "",
    dry_run: bool = False,
) -> PublishResult:
    gid = resolve_vk_group_id(token, group_id) if not dry_run else group_id
    attachment = ""

    if cover and cover.exists():
        if user_token:
            if dry_run:
                attachment = "[dry-run photo]"
            else:
                attachment = upload_vk_wall_photo(user_token, int(gid), cover)
        else:
            print(
                "⚠ VK: для картинки нужен VK_USER_TOKEN (ключ сообщества фото не грузит). "
                "См. checklists/vk-photo-token.md",
                file=sys.stderr,
            )

    if dry_run:
        mode = "текст+фото" if attachment else "текст"
        return PublishResult("vk", True, f"[dry-run] → группа {group_id} ({mode})")

    payload: dict[str, Any] = {
        "access_token": token,
        "v": "5.199",
        "owner_id": f"-{gid}",
        "from_group": 1,
        "message": text,
    }
    if attachment:
        payload["attachments"] = attachment

    resp = requests.post("https://api.vk.com/method/wall.post", data=payload, timeout=60)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"VK API wall.post: {data['error']}")
    post_id = data["response"]["post_id"]
    return PublishResult("vk", True, f"Пост #{post_id}", post_id)


def require_approved(item: dict[str, Any], force: bool) -> None:
    if item.get("status") != "approved" and not force:
        raise SystemExit(
            f"Статус «{item.get('status')}». Сначала: python publish.py queue approve {item['id']}"
        )


def require_post_approved(item: dict[str, Any] | None, post_id: str, force: bool) -> None:
    if force:
        return
    if not item:
        raise SystemExit(
            f"Нет {post_id} в queue/posts-queue.yaml. Добавьте запись и: python publish.py queue approve {post_id}"
        )
    if item.get("status") != "approved":
        raise SystemExit(
            f"Статус «{item.get('status')}». Сначала: python publish.py queue approve {post_id}"
        )


def resolve_post_path(post_id: str, platform: str) -> Path:
    posts = load_posts_queue()
    item = find_posts_item(posts, post_id)
    if item and item.get("post"):
        return ROOT / item["post"]
    sub = "tg" if platform == "tg" else "vk"
    return ROOT / "articles" / sub / f"{post_id}.md"


def ensure_post_cover(post_id: str, post_path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    posts = load_posts_queue()
    item = find_posts_item(posts, post_id)
    if item and item.get("cover"):
        cover = ROOT / item["cover"]
        if cover.exists():
            vk_cover = cover.with_name(f"{cover.stem}-vk{cover.suffix}")
            if item.get("platform") == "vk" and not vk_cover.exists():
                try:
                    from generate_cover import ensure_covers

                    headline = item.get("cover_headline", "")
                    subline = item.get("cover_subline", "")
                    if not headline:
                        from generate_cover import _headline_from_post

                        headline, subline = _headline_from_post(post_path)
                    ensure_covers(cover.stem.replace("-vk", ""), headline, subline)
                except Exception as exc:
                    print(f"⚠ обложка VK: {exc}", file=sys.stderr)
            return
    try:
        from generate_cover import ensure_cover_for_post

        ensure_cover_for_post(post_id, post_path)
    except Exception as exc:
        print(f"⚠ обложка {post_id}: {exc}", file=sys.stderr)


def mark_post_published(post_id: str) -> None:
    posts = load_posts_queue()
    item = find_posts_item(posts, post_id)
    if not item:
        return
    item["status"] = "published"
    item["published_at"] = datetime.now(timezone.utc).isoformat()
    for i, it in enumerate(posts):
        if it.get("id") == post_id:
            posts[i] = item
            break
    save_posts_queue(posts)


def resolve_cover_path(item: dict[str, Any], *, vk: bool = False) -> Path | None:
    rel = item.get("cover")
    if not rel:
        return None
    base = ROOT / rel
    if vk:
        vk_path = base.with_name(f"{base.stem}-vk{base.suffix}")
        if vk_path.exists():
            return vk_path
    return base if base.exists() else None


def ensure_campaign_covers(campaign_id: str, *, dry_run: bool) -> None:
    try:
        from generate_cover import ensure_cover_for_queue_id

        path = ensure_cover_for_queue_id(campaign_id)
        if path:
            print(f"Обложка: {path.relative_to(ROOT)}")
    except Exception as exc:
        print(f"⚠ не удалось сгенерировать обложку: {exc}", file=sys.stderr)


def resolve_standalone_cover(post_id: str, *, vk: bool = False) -> Path | None:
    base = ROOT / "assets" / "covers" / f"{post_id}.jpg"
    if vk:
        vk_path = base.with_name(f"{post_id}-vk.jpg")
        if vk_path.exists():
            return vk_path
    return base if base.exists() else None


def ensure_standalone_cover(post_id: str, path: Path) -> Path | None:
    """Генерирует обложку для отдельного TG/VK-поста, если файла ещё нет."""
    cover = resolve_standalone_cover(post_id)
    if cover:
        return cover
    try:
        from generate_cover import ensure_cover_for_post

        return ensure_cover_for_post(post_id, path)
    except Exception as exc:
        print(f"⚠ обложка для {post_id}: {exc}", file=sys.stderr)
        return None


def publish_dzen_article(
    item: dict[str, Any], *, dry_run: bool, token: str, channel: str
) -> None:
    path = article_path(item)
    if not path:
        raise SystemExit("В очереди нет dzen_article")
    article = load_article(resolve_path(path))
    text = format_for_dzen(article)
    cover = resolve_cover_path(item)
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

    cover_tg = resolve_cover_path(item)
    cover_vk = resolve_cover_path(item, vk=True) or cover_tg

    tg_path = teaser_tg_path(item)
    if tg_path and main_ch and token:
        text = replace_dzen_url(load_tg_post(resolve_path(tg_path)), url)
        r = publish_telegram(
            text, main_ch, token, cover=cover_tg, dry_run=dry_run, parse_mode="HTML"
        )
        print(f"TG тизер ({main_ch}): {r.message}")

    vk_path = teaser_vk_path(item)
    if vk_path and vk_token and vk_group:
        text = replace_dzen_url(load_plain_post(resolve_path(vk_path)), url)
        user_token = os.getenv("VK_USER_TOKEN", "")
        r = publish_vk(
            text, vk_token, vk_group, cover=cover_vk, user_token=user_token, dry_run=dry_run
        )
        print(f"VK тизер: {r.message}")
    elif vk_path and not dry_run:
        print("ℹ VK: задайте VK_ACCESS_TOKEN и VK_GROUP_ID в .env")


def publish_standalone_tg(post_id: str, *, dry_run: bool, force: bool) -> int:
    posts = load_posts_queue()
    post_item = find_posts_item(posts, post_id)
    require_post_approved(post_item, post_id, force)

    campaign_items = load_queue()
    campaign = find_queue_item(campaign_items, post_id)
    if campaign and campaign.get("tg_post"):
        require_approved(campaign, force)
        path = campaign["tg_post"]
    elif post_item and post_item.get("post"):
        path = post_item["post"]
    else:
        path = f"articles/tg/{post_id}.md"

    resolved = resolve_path(path)
    ensure_post_cover(post_id, resolved, dry_run=dry_run)
    text = load_tg_post(resolved)
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    ch = os.environ["TELEGRAM_MAIN_CHANNEL_ID"]
    cover = resolve_standalone_cover(post_id) or ensure_standalone_cover(post_id, resolved)
    r = publish_telegram(text, ch, token, cover=cover, dry_run=dry_run, parse_mode="HTML")
    print(f"TG пост ({ch}): {r.message}")
    if not dry_run and post_item:
        mark_post_published(post_id)
    return 0


def publish_standalone_vk(post_id: str, *, dry_run: bool, force: bool) -> int:
    posts = load_posts_queue()
    post_item = find_posts_item(posts, post_id)
    require_post_approved(post_item, post_id, force)

    campaign_items = load_queue()
    campaign = find_queue_item(campaign_items, post_id)
    if campaign and campaign.get("vk_post") and not campaign.get("dzen_teaser_vk"):
        require_approved(campaign, force)
        path = campaign["vk_post"]
    elif post_item and post_item.get("post"):
        path = post_item["post"]
    else:
        path = f"articles/vk/{post_id}.md"

    resolved = resolve_path(path)
    ensure_post_cover(post_id, resolved, dry_run=dry_run)
    text = load_plain_post(resolved)
    cover = resolve_standalone_cover(post_id, vk=True) or resolve_standalone_cover(post_id)
    if not cover:
        cover = ensure_standalone_cover(post_id, resolved)
    user_token = os.getenv("VK_USER_TOKEN", "")
    r = publish_vk(
        text,
        os.environ["VK_ACCESS_TOKEN"],
        os.environ["VK_GROUP_ID"],
        cover=cover,
        user_token=user_token,
        dry_run=dry_run,
    )
    print(f"VK пост: {r.message}")
    if not dry_run and post_item:
        mark_post_published(post_id)
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

    if target in ("dzen", "teasers", "teasers-vk", "all"):
        ensure_campaign_covers(item_id, dry_run=dry_run)

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

    if target in ("teasers", "teasers-vk", "all"):
        if target in ("teasers", "teasers-vk"):
            require_approved(item, force)
        vk_only = target == "teasers-vk"
        if not vk_only:
            if not token or not main_ch:
                raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_MAIN_CHANNEL_ID")
        if vk_only or (token and main_ch):
            publish_dzen_teasers(
                item, dry_run=dry_run, token=token, main_ch=main_ch if not vk_only else "",
                vk_token=vk_token, vk_group=vk_group,
            )

    if target == "all" and not dry_run:
        item["status"] = "published"
        item["published_at"] = datetime.now(timezone.utc).isoformat()
        save_queue(items)

    if dry_run:
        print("\n[dry-run] Для реальной публикации: DRY_RUN=false python publish.py publish", target, item_id)
    return 0


def load_schedule() -> dict[str, Any]:
    if not SCHEDULE_FILE.exists():
        return {"timezone": "Europe/Moscow", "slots": []}
    return yaml.safe_load(SCHEDULE_FILE.read_text(encoding="utf-8")) or {"slots": []}


def save_schedule(data: dict[str, Any]) -> None:
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def now_msk() -> datetime:
    return datetime.now(MSK)


def slot_when(slot: dict[str, Any]) -> datetime:
    return datetime.strptime(f"{slot['date']} {slot['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=MSK)


def schedule_uses_live_publish() -> bool:
    """AUTO_PUBLISH=true в .env — расписание публикует по-настоящему."""
    return env_bool("AUTO_PUBLISH", False)


def fetch_dzen_url_by_title(title: str, channel: str = DZEN_CHANNEL_SLUG) -> str:
    resp = requests.get(
        f"https://dzen.ru/api/v3/launcher/export?channel_name={channel}",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    resp.raise_for_status()
    needle = title.lower().strip().rstrip(".")[:50]
    for item in resp.json().get("items", []):
        t = (item.get("title") or "").lower().strip()
        if needle in t or t[:50] in needle:
            link = item.get("share_link") or ""
            if link:
                return link
    return ""


def sync_dzen_url(campaign_id: str) -> str:
    items = load_queue()
    item = find_queue_item(items, campaign_id)
    if not item or item.get("dzen_url"):
        return item.get("dzen_url", "") if item else ""
    path = article_path(item)
    if not path:
        return ""
    article = load_article(resolve_path(path))
    url = fetch_dzen_url_by_title(article.title)
    if url:
        item["dzen_url"] = url
        save_queue(items)
        print(f"✓ dzen_url для {campaign_id}: {url}")
    return url


def execute_schedule_slot(slot: dict[str, Any], *, dry_run: bool) -> tuple[bool, str]:
    action = slot.get("action", "")
    cid = slot.get("campaign_id") or slot.get("post_id") or ""

    if action == "vc_manual":
        return True, "VC вручную — пропуск"

    if action == "publish_dzen":
        items = load_queue()
        item = find_queue_item(items, cid)
        if not item:
            return False, f"нет кампании {cid}"
        if item.get("status") not in ("approved", "published") and not dry_run:
            return False, f"статус {item.get('status')} — нужен approved"
        ensure_campaign_covers(cid, dry_run=dry_run)
        cmd_publish("dzen", cid, dry_run=dry_run, force=True)
        if not dry_run:
            items = load_queue()
            item = find_queue_item(items, cid)
            if item:
                item["dzen_published_at"] = now_msk().isoformat()
                if item.get("status") == "approved":
                    item["status"] = "published"
                save_queue(items)
        return True, f"dzen {cid}"

    if action == "publish_teasers":
        sync_dzen_url(cid)
        items = load_queue()
        item = find_queue_item(items, cid)
        if not item:
            return False, f"нет кампании {cid}"
        if not item.get("dzen_url") and not dry_run:
            return False, "dzen_url ещё нет — повторим позже (синхробот 2–10 мин)"
        ensure_campaign_covers(cid, dry_run=dry_run)
        cmd_publish("teasers", cid, dry_run=dry_run, force=True)
        return True, f"teasers {cid}"

    if action == "publish_tg_post":
        post_id = slot.get("post_id") or cid
        posts = load_posts_queue()
        post_item = find_posts_item(posts, post_id)
        if post_item and post_item.get("status") not in ("approved", "published") and not dry_run:
            return False, f"статус {post_item.get('status')} — нужен approved (ок {post_id})"
        path = resolve_post_path(post_id, "tg")
        if not path.exists():
            return False, f"нет файла {path.relative_to(ROOT)}"
        ensure_post_cover(post_id, path, dry_run=dry_run)
        publish_standalone_tg(post_id, dry_run=dry_run, force=True)
        return True, f"tg-post {post_id}"

    if action == "publish_vk_post":
        post_id = slot.get("post_id") or cid
        posts = load_posts_queue()
        post_item = find_posts_item(posts, post_id)
        if post_item and post_item.get("status") not in ("approved", "published") and not dry_run:
            return False, f"статус {post_item.get('status')} — нужен approved (ок {post_id})"
        path = resolve_post_path(post_id, "vk")
        if not path.exists():
            return False, f"нет файла {path.relative_to(ROOT)}"
        ensure_post_cover(post_id, path, dry_run=dry_run)
        publish_standalone_vk(post_id, dry_run=dry_run, force=True)
        return True, f"vk-post {post_id}"

    return False, f"неизвестное действие {action}"


def cmd_schedule_run(args: argparse.Namespace) -> int:
    load_env()
    dry = args.dry_run or (not schedule_uses_live_publish())
    if dry and not args.dry_run:
        print("ℹ AUTO_PUBLISH не включён — dry-run. Задайте AUTO_PUBLISH=true в .env")

    data = load_schedule()
    slots: list[dict[str, Any]] = data.get("slots", [])
    now = now_msk()
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        day = now.date()

    ran = 0
    for slot in slots:
        status = slot.get("status", "scheduled")
        if status not in ("scheduled", "pending"):
            continue
        when = slot_when(slot)
        if when.date() != day:
            continue
        if not args.force and when > now:
            continue

        label = f"{slot['date']} {slot['time']} {slot.get('action')} {slot.get('campaign_id') or slot.get('post_id', '')}"
        print(f"\n→ {label}")
        try:
            ok, msg = execute_schedule_slot(slot, dry_run=dry)
            print(f"  {'✓' if ok else '✗'} {msg}")
            if ok:
                slot["status"] = "done"
                slot["completed_at"] = now.isoformat()
                ran += 1
            elif status == "scheduled" and slot.get("action") == "publish_teasers":
                slot["status"] = "pending"
                print("  ↻ pending — повтор при следующем запуске")
            else:
                slot["status"] = "failed"
                slot["error"] = msg
        except Exception as exc:
            slot["status"] = "failed"
            slot["error"] = str(exc)
            print(f"  ✗ {exc}")

    save_schedule(data)
    print(f"\nГотово: {ran} слотов" + (" (dry-run)" if dry else ""))
    return 0


def cmd_schedule_prepare_covers(args: argparse.Namespace) -> int:
    """Обложки для слотов на сегодня (и ближайшие approved посты)."""
    load_env()
    data = load_schedule()
    now = now_msk()
    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else now.date()
    n = 0
    for slot in data.get("slots", []):
        if slot.get("status") not in ("scheduled", "pending"):
            continue
        when = slot_when(slot)
        if when.date() != day:
            continue
        action = slot.get("action", "")
        cid = slot.get("campaign_id") or slot.get("post_id") or ""
        try:
            if action in ("publish_dzen", "publish_teasers"):
                ensure_campaign_covers(cid, dry_run=False)
                n += 1
            elif action == "publish_tg_post":
                path = resolve_post_path(cid, "tg")
                if path.exists():
                    ensure_post_cover(cid, path, dry_run=False)
                    n += 1
            elif action == "publish_vk_post":
                path = resolve_post_path(cid, "vk")
                if path.exists():
                    ensure_post_cover(cid, path, dry_run=False)
                    n += 1
        except Exception as exc:
            print(f"⚠ cover {cid}: {exc}", file=sys.stderr)
    print(f"Обложки подготовлены: {n}")
    return 0


def cmd_schedule_sync_urls(_args: argparse.Namespace) -> int:
    load_env()
    items = load_queue()
    n = 0
    for item in items:
        if item.get("dzen_url"):
            continue
        if not article_path(item):
            continue
        if sync_dzen_url(item["id"]):
            n += 1
    print(f"Обновлено dzen_url: {n}")
    return 0


def cmd_schedule_list(_args: argparse.Namespace) -> int:
    data = load_schedule()
    now = now_msk()
    for slot in data.get("slots", []):
        when = slot_when(slot)
        mark = "← сейчас" if slot.get("status") in ("scheduled", "pending") and when <= now else ""
        cid = slot.get("campaign_id") or slot.get("post_id", "")
        print(f"{slot['date']} {slot['time']} [{slot.get('status')}] {slot.get('action')} {cid} {mark}")
    return 0


def cmd_vk_attach_cover(args: argparse.Namespace) -> int:
    load_env()
    community = os.getenv("VK_ACCESS_TOKEN", "")
    user = os.getenv("VK_USER_TOKEN", "")
    group = os.getenv("VK_GROUP_ID", "")
    if not all([community, user, group]):
        raise SystemExit("Нужны VK_ACCESS_TOKEN, VK_USER_TOKEN, VK_GROUP_ID в .env")

    items = load_queue()
    item = find_queue_item(items, args.id)
    if not item or not item.get("cover"):
        raise SystemExit("Нет cover в очереди для этого id")
    cover = ROOT / item["cover"]
    gid = resolve_vk_group_id(community, group)
    attachment = upload_vk_wall_photo(user, gid, cover)

    message = ""
    vk_path = teaser_vk_path(item)
    if vk_path:
        message = replace_dzen_url(load_plain_post(resolve_path(vk_path)), item.get("dzen_url", ""))
    else:
        post = vk_api("wall.getById", user, posts=f"-{gid}_{args.post_id}")
        message = post["items"][0].get("text", "")

    resp = requests.post(
        "https://api.vk.com/method/wall.edit",
        data={
            "access_token": user,
            "v": "5.199",
            "owner_id": -gid,
            "post_id": args.post_id,
            "message": message,
            "attachments": attachment,
        },
        timeout=60,
    ).json()
    if "error" in resp:
        raise SystemExit(f"wall.edit: {resp['error']}")
    print(f"✓ К посту {args.post_id} прикреплено фото")
    print(f"  https://vk.ru/wall-{gid}_{args.post_id}")
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
        choices=["dzen", "teasers", "teasers-vk", "all", "tg-post", "vk-post"],
        help="teasers-vk=только VK; teasers=TG+VK",
    )
    pub.add_argument("id")
    pub.add_argument("--dry-run", action="store_true")
    pub.add_argument("--force", action="store_true")

    fmt = sub.add_parser("format")
    fmt.add_argument("article", help="путь от автоматизация-контента/")

    p_cov = sub.add_parser("vk-attach-cover", help="Добавить обложку к существующему посту VK")
    p_cov.add_argument("post_id", type=int, help="Номер поста, напр. 204")
    p_cov.add_argument("id", help="id в очереди (для пути к cover)")

    sch = sub.add_parser("schedule", help="Автопубликация по posting-schedule.yaml")
    schs = sch.add_subparsers(dest="schedule_cmd", required=True)
    sch_run = schs.add_parser("run", help="Выполнить слоты на сегодня (или --date)")
    sch_run.add_argument("--dry-run", action="store_true")
    sch_run.add_argument("--force", action="store_true", help="Игнорировать время слота")
    sch_run.add_argument("--date", help="YYYY-MM-DD")
    schs.add_parser("list", help="Показать расписание")
    schs.add_parser("sync-urls", help="Подтянуть dzen_url из API Дзена")
    sch_prep = schs.add_parser("prepare-covers", help="Обложки для слотов на дату")
    sch_prep.add_argument("--date", help="YYYY-MM-DD")

    cov = sub.add_parser("cover", help="Генерация обложек GPT/PIL")
    cov.add_argument("campaign_id", help="id кампании из очереди")
    cov.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.command == "cover":
        from generate_cover import ensure_cover_for_queue_id

        load_env()
        path = ensure_cover_for_queue_id(args.campaign_id, force=args.force)
        if not path:
            raise SystemExit("Не удалось сгенерировать обложку")
        print(path)
        return 0

    if args.command == "schedule":
        if args.schedule_cmd == "run":
            return cmd_schedule_run(args)
        if args.schedule_cmd == "list":
            return cmd_schedule_list(args)
        if args.schedule_cmd == "sync-urls":
            return cmd_schedule_sync_urls(args)
        if args.schedule_cmd == "prepare-covers":
            return cmd_schedule_prepare_covers(args)

    if args.command == "vk-attach-cover":
        return cmd_vk_attach_cover(args)

    if args.command == "queue":
        if args.queue_cmd == "list":
            print("=== Кампании Дзен (publish-queue) ===")
            for item in load_queue():
                print(
                    f"- {item['id']}: {item.get('status', '?')} | "
                    f"dzen: {article_path(item) or '—'}"
                )
            print("\n=== Свои посты TG/VK (posts-queue) ===")
            for item in load_posts_queue():
                print(
                    f"- {item['id']}: {item.get('status', '?')} | "
                    f"{item.get('platform', '?')} | {item.get('post', '—')}"
                )
            return 0
        if args.queue_cmd == "approve":
            items = load_queue()
            item = find_queue_item(items, args.id)
            if item:
                item["status"] = "approved"
                item["approved_at"] = datetime.now(timezone.utc).isoformat()
                save_queue(items)
                print(f"✓ кампания {args.id} → approved")
                return 0
            posts = load_posts_queue()
            post = find_posts_item(posts, args.id)
            if post:
                post["status"] = "approved"
                post["approved_at"] = datetime.now(timezone.utc).isoformat()
                save_posts_queue(posts)
                print(f"✓ пост {args.id} → approved")
                return 0
            print(f"✗ нет id {args.id} в publish-queue или posts-queue")
            return 1

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
