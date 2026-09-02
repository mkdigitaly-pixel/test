#!/usr/bin/env python3
"""
Публикация mkekspert: 4 потока контента.

  dzen/articles  → RSS/HTML (по умолчанию) или TELEGRAM_DZEN_CHANNEL → @zen_sync_bot (только ≤1024)
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
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
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
    inline_images: list[Path] = field(default_factory=list)


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


def _is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\|[\s\-:|]+\|$", line.strip()))


def _parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _format_markdown_table(table_lines: list[str]) -> list[str]:
    if len(table_lines) < 2:
        return table_lines
    headers = _parse_table_row(table_lines[0])
    rows: list[str] = []
    for line in table_lines[2:]:
        if not line.strip().startswith("|"):
            break
        cells = _parse_table_row(line)
        if len(cells) != len(headers):
            continue
        if len(cells) == 3:
            rows.append(f"— {cells[0]}: было {cells[1]}, стало {cells[2]}")
        elif len(cells) == 2:
            rows.append(f"— {cells[0]}: {cells[1]}")
        else:
            rows.append("— " + " · ".join(cells))
    return rows or table_lines


def _resolve_image_path(rel: str, base_dir: Path | None) -> Path | None:
    candidates: list[Path] = []
    path = Path(rel)
    if path.is_absolute():
        candidates.append(path)
    if base_dir:
        candidates.append(base_dir / rel)
    candidates.append(ROOT / rel)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _strip_inline_markdown(line: str) -> str:
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"__([^_]+)__", r"\1", line)
    line = re.sub(r"~~([^~]+)~~", r"\1", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", line)


def markdown_to_dzen(md: str, *, base_dir: Path | None = None) -> tuple[str, list[Path]]:
    """Plain text для @zen_sync_bot: H2/H3, таблицы → списки, без markdown-мусора."""
    lines_out: list[str] = []
    inline_images: list[Path] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            i += 1
            continue

        if line.strip().startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            lines_out.extend(_format_markdown_table(table_lines))
            lines_out.append("")
            continue

        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line.strip())
        if img_match:
            image_path = _resolve_image_path(img_match.group(2), base_dir)
            if image_path:
                inline_images.append(image_path)
            i += 1
            continue

        if line.startswith("#"):
            header = re.sub(r"^#+\s*", "", line).strip()
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            lines_out.append(header)
            lines_out.append("")
            i += 1
            continue

        lines_out.append(_strip_inline_markdown(line))
        i += 1

    text = "\n".join(lines_out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), inline_images


def markdown_to_plain(md: str) -> str:
    text, _ = markdown_to_dzen(md)
    return text


def split_text_at_paragraphs(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for para in re.split(r"\n\n+", text):
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(para) <= limit:
            current = para
            continue
        start = 0
        while start < len(para):
            chunks.append(para[start : start + limit])
            start += limit
        current = ""
    if current:
        chunks.append(current)
    return chunks


def _inline_dzen_html(line: str) -> str:
    line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"__([^_]+)__", r"<i>\1</i>", line)
    line = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)


def markdown_to_dzen_html(md: str, *, base_dir: Path | None = None) -> str:
    """HTML для Дзена (RSS / вставка в Студию): whitelist по dzen.ru/help RSS."""
    blocks: list[str] = []
    lines = md.splitlines()
    i = 0
    list_buf: list[str] = []
    list_ordered = False

    def flush_list() -> None:
        nonlocal list_buf, list_ordered
        if not list_buf:
            return
        tag = "ol" if list_ordered else "ul"
        items = "".join(f"<li>{_inline_dzen_html(item)}</li>" for item in list_buf)
        blocks.append(f"<{tag}>{items}</{tag}>")
        list_buf = []
        list_ordered = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped == "---":
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and _is_table_separator(lines[i + 1]):
            flush_list()
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            for row in _format_markdown_table(table_lines):
                blocks.append(f"<p>{_inline_dzen_html(row)}</p>")
            continue

        if stripped.startswith("### "):
            flush_list()
            blocks.append(f"<h3>{_inline_dzen_html(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            flush_list()
            blocks.append(f"<h2>{_inline_dzen_html(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            flush_list()
            blocks.append(f"<h2>{_inline_dzen_html(stripped[2:])}</h2>")
            i += 1
            continue

        img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if img_match:
            flush_list()
            alt, rel = img_match.group(1), img_match.group(2)
            src = str(_resolve_image_path(rel, base_dir) or rel)
            cap = f"<figcaption>{alt}</figcaption>" if alt else ""
            blocks.append(f'<figure><img src="{src}"/>{cap}</figure>')
            i += 1
            continue

        if stripped.startswith("> "):
            flush_list()
            blocks.append(f"<blockquote><p>{_inline_dzen_html(stripped[2:])}</p></blockquote>")
            i += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_list()
            if list_buf and not list_ordered:
                flush_list()
            list_ordered = True
            list_buf.append(re.sub(r"^\d+\.\s+", "", stripped))
            i += 1
            continue

        if stripped.startswith("— ") or stripped.startswith("- "):
            if list_buf and list_ordered:
                flush_list()
            list_buf.append(stripped[2:])
            i += 1
            continue

        if not stripped:
            flush_list()
            i += 1
            continue

        flush_list()
        blocks.append(f"<p>{_inline_dzen_html(stripped)}</p>")
        i += 1

    flush_list()
    return "\n".join(blocks)


def article_to_dzen_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    meta, body_md = parse_frontmatter(raw)
    title = str(meta.get("h1") or meta.get("title") or "").strip()
    body_html = markdown_to_dzen_html(body_md, base_dir=path.parent)
    if title:
        return f"<h1>{title}</h1>\n{body_html}"
    return body_html


def write_dzen_html_export(article_path: Path, *, cover_rel: str | None = None) -> Path:
    html_body = article_to_dzen_html(article_path)
    if cover_rel:
        from dzen_rss import cover_public_url, prepend_cover_html

        html_body = prepend_cover_html(html_body, cover_public_url(cover_rel))
    out_dir = ROOT / "articles" / "dzen" / "html"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{article_path.stem}.html"
    out_path.write_text(html_body + "\n", encoding="utf-8")
    return out_path


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
    body, inline_images = markdown_to_dzen(body_md, base_dir=path.parent)
    if body.startswith(title):
        body = body[len(title) :].lstrip("\n")
    utm = str(meta.get("utm_campaign") or "article")
    return Article(
        title=title,
        body=body,
        utm_campaign=utm,
        source_path=path,
        inline_images=inline_images,
    )


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
    long_post_with_cover: bool = True,
) -> PublishResult:
    """TG: до 4096 знаков (Premium). Фото+длинный текст — reply к обложке."""
    if len(text) > TG_MESSAGE_LIMIT:
        raise ValueError(f"Текст {len(text)} символов — лимит Telegram {TG_MESSAGE_LIMIT}.")

    if dry_run:
        if cover and len(text) <= TG_CAPTION_LIMIT:
            mode = "фото+текст"
        elif cover and long_post_with_cover:
            mode = f"фото+reply ({len(text)} зн.)"
        else:
            mode = "текст"
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

    reply_to: int | None = None
    if cover and cover.exists() and len(text) > TG_CAPTION_LIMIT:
        if long_post_with_cover:
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
            reply_to = data["result"]["message_id"]
        else:
            print("⚠ Текст >1024 — публикуем без обложки.", file=sys.stderr)

    payload: dict[str, Any] = {
        "chat_id": channel_id,
        "text": text,
        "disable_web_page_preview": False,
        **msg_extra,
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    data = telegram_api("sendMessage", payload, token)
    mode = "Фото + длинный текст (reply)" if reply_to else "Текст опубликован"
    return PublishResult("telegram", True, mode, data["result"]["message_id"])


def publish_telegram_media_group(
    images: list[Path],
    caption: str,
    channel_id: str,
    token: str,
    *,
    dry_run: bool = False,
) -> PublishResult:
    if not images:
        raise ValueError("Нет изображений для media group")
    if len(caption) > TG_CAPTION_LIMIT:
        raise ValueError(f"Подпись {len(caption)} символов — лимит {TG_CAPTION_LIMIT}.")

    if dry_run:
        preview = caption[:400] + ("…" if len(caption) > 400 else "")
        names = ", ".join(p.name for p in images[:3])
        return PublishResult(
            "telegram",
            True,
            f"[dry-run] → {channel_id} (album {len(images)}: {names})\n{preview}",
        )

    media: list[dict[str, Any]] = []
    files: dict[str, Any] = {}
    for idx, image in enumerate(images[:10]):
        key = f"photo{idx}"
        media.append({"type": "photo", "media": f"attach://{key}"})
        files[key] = image.open("rb")
    media[0]["caption"] = caption

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMediaGroup",
            data={"chat_id": channel_id, "media": json.dumps(media)},
            files=files,
            timeout=120,
        )
    finally:
        for handle in files.values():
            handle.close()

    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", data))
    message_id = data["result"][0]["message_id"] if data.get("result") else None
    return PublishResult("telegram", True, f"Альбом ({len(images)} фото)", message_id)


def publish_telegram_document(
    channel_id: str,
    token: str,
    doc_path: Path,
    *,
    caption: str = "",
    dry_run: bool = False,
) -> PublishResult:
    if dry_run:
        return PublishResult(
            "telegram",
            True,
            f"[dry-run] → {channel_id} (документ {doc_path.name})\n{caption[:200]}",
        )
    data_payload: dict[str, Any] = {"chat_id": channel_id}
    if caption:
        data_payload["caption"] = caption[:TG_CAPTION_LIMIT]
    with doc_path.open("rb") as f:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=data_payload,
            files={"document": f},
            timeout=120,
        )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", data))
    return PublishResult("telegram", True, f"Документ {doc_path.name}", data["result"]["message_id"])


def notify_dzen_rss_channel(
    channel_id: str,
    token: str,
    *,
    title: str,
    html_path: Path,
    cover: Path | None,
    feed_url: str,
    dry_run: bool,
) -> None:
    """Служебное уведомление в DZEN-канал: HTML-файл + обложка. Не полный текст (zen_sync без разметки)."""
    caption = (
        f"📄 {title}\n\n"
        "Статья в RSS — Дзен подхватит с разметкой (жирный, H2, ссылки, обложка).\n"
        f"Лента: {feed_url}\n\n"
        "⚠ Не публикуйте сюда полный текст — @zen_sync_bot съест разметку."
    )
    if cover and cover.exists():
        publish_telegram(
            caption,
            channel_id,
            token,
            cover=cover,
            dry_run=dry_run,
            long_post_with_cover=False,
        )
    else:
        publish_telegram(caption, channel_id, token, dry_run=dry_run)
    if html_path.exists():
        publish_telegram_document(channel_id, token, html_path, caption=title, dry_run=dry_run)


def dzen_routing(text: str, mode: str) -> tuple[bool, bool]:
    """(sync в TG, RSS). Длинные статьи — только RSS: zen_sync даёт 2 поста при фото+текст."""
    mode = mode.lower()
    long = len(text) > TG_CAPTION_LIMIT
    if mode == "rss":
        return False, True
    if mode == "sync":
        if long:
            print(
                f"⚠ sync невозможен для {len(text)} зн. — переключаюсь на RSS",
                file=sys.stderr,
            )
            return False, True
        return True, False
    if mode == "both":
        return not long, True
    # auto: короткие → sync (фото+текст в одном сообщении), длинные → rss
    return (not long, long)


def publish_dzen_telegram(
    text: str,
    channel_id: str,
    token: str,
    *,
    cover: Path | None = None,
    inline_images: list[Path] | None = None,
    dry_run: bool = False,
) -> PublishResult:
    """Публикация в DZEN-канал с учётом лимитов @zen_sync_bot."""
    images: list[Path] = []
    if cover and cover.exists():
        images.append(cover)
    for image in inline_images or []:
        if image.exists() and image not in images:
            images.append(image)

    if len(text) <= TG_CAPTION_LIMIT and images:
        if len(images) == 1:
            return publish_telegram(text, channel_id, token, cover=images[0], dry_run=dry_run)
        return publish_telegram_media_group(images, text, channel_id, token, dry_run=dry_run)

    if len(text) > TG_CAPTION_LIMIT and images:
        cover_hint = images[0] if images else "assets/covers/"
        print(
            f"ℹ Длинная статья ({len(text)} зн.): zen_sync не принимает фото+текст в одном посте — "
            f"используйте RSS (обложка: {cover_hint})",
            file=sys.stderr,
        )

    if len(text) <= TG_MESSAGE_LIMIT:
        return publish_telegram(text, channel_id, token, dry_run=dry_run)

    chunks = split_text_at_paragraphs(text, TG_MESSAGE_LIMIT)
    print(
        f"⚠ Текст {len(text)} символов — {len(chunks)} сообщений (лимит TG 4096). "
        "Сократите статью или разбейте на части.",
        file=sys.stderr,
    )
    result: PublishResult | None = None
    for chunk in chunks:
        result = publish_telegram(chunk, channel_id, token, dry_run=dry_run)
    return result or PublishResult("telegram", False, "Пустой текст")


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
    mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    with image_path.open("rb") as f:
        up = requests.post(
            up_srv["upload_url"],
            files={"photo": (image_path.name or "cover.jpg", f, mime)},
            timeout=120,
        ).json()
    if not up.get("photo"):
        raise RuntimeError(f"VK upload: пустой photo (server={up.get('server')}, hash={up.get('hash')})")
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
    from dzen_rss import FEED_FILE, FEED_LINK, cover_public_url, deploy_rss_public, rss_draft_mode, upsert_article_item

    rel = article_path(item)
    if not rel:
        raise SystemExit("В очереди нет dzen_article")
    path = resolve_path(rel)
    raw = path.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(raw)
    title = str(meta.get("h1") or meta.get("title") or "").strip()
    description = str(meta.get("description") or title).strip()
    article = load_article(path)
    text = format_for_dzen(article)
    cover_rel = str(item.get("cover") or "")
    cover = resolve_cover_path(item)

    html_path = write_dzen_html_export(path, cover_rel=cover_rel or None)
    body_html = html_path.read_text(encoding="utf-8")
    mode = os.getenv("DZEN_PUBLISH_MODE", "auto").lower()
    use_sync, use_rss = dzen_routing(text, mode)

    if not dry_run and use_rss:
        upsert_article_item(
            campaign_id=item["id"],
            article_path=path,
            title=title,
            description=description,
            body_html=body_html,
            cover_rel=cover_rel or None,
        )

    if use_sync:
        if not token or not channel:
            raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_DZEN_CHANNEL_ID")
        r = publish_dzen_telegram(
            text,
            channel,
            token,
            cover=cover,
            inline_images=article.inline_images,
            dry_run=dry_run,
        )
        print(f"DZEN-канал ({channel}): {r.message}")
        if not dry_run:
            print("  → Синхробот подхватит в Дзен за 2–10 мин")
        if not use_rss:
            return

    if not use_rss:
        return

    if len(text) > TG_CAPTION_LIMIT:
        print(
            f"Дзен: длинная статья ({len(text)} зн.) → RSS, без поста в zen_sync-канал "
            "(фото+текст = 2 поста в Дзене)"
        )

    draft = rss_draft_mode()
    deployed: list[str] = []
    if not dry_run:
        deployed = deploy_rss_public(campaign_id=item["id"], cover_rel=cover_rel or None, dry_run=dry_run)

    print("Дзен: RSS + HTML (автоматически, с разметкой)")
    print(f"  HTML: {html_path}")
    print(f"  RSS:  {FEED_FILE}")
    for line in deployed:
        print(f"  Deploy: {line}")
    print(f"  Публичная лента: {FEED_LINK}")
    print(f"  Обложка: {cover_public_url(cover_rel) or cover or '—'}")
    print(f"  Режим: {'черновик (native-draft)' if draft else 'автопубликация'}")

    notify_ch = os.getenv("DZEN_TG_NOTIFY_CHANNEL", "").strip()
    notify = os.getenv("DZEN_TG_NOTIFY", "false").lower() in ("1", "true", "yes")
    if notify and notify_ch and token:
        notify_dzen_rss_channel(
            notify_ch,
            token,
            title=title,
            html_path=html_path,
            cover=cover,
            feed_url=FEED_LINK,
            dry_run=dry_run,
        )
        print(f"  TG ({notify_ch}): уведомление о публикации")
    elif notify and not notify_ch:
        print(
            "  ℹ DZEN_TG_NOTIFY=true, но DZEN_TG_NOTIFY_CHANNEL пуст — уведомление пропущено",
            file=sys.stderr,
        )

    if not dry_run:
        item["dzen_rss_pending"] = not draft
        item["dzen_html_path"] = str(html_path.relative_to(ROOT))
        item["dzen_feed_url"] = FEED_LINK
        print("  → Дзен заберёт RSS автоматически; dzen_url подтянется через schedule sync-urls")


def publish_dzen_teasers(
    item: dict[str, Any], *, dry_run: bool, token: str, main_ch: str, vk_token: str, vk_group: str
) -> None:
    url = item.get("dzen_url", "")
    if not url and not dry_run:
        url = sync_dzen_url(item["id"])
    if not url and not dry_run:
        print("⚠ dzen_url ещё нет — schedule повторит тизеры автоматически", file=sys.stderr)

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
        mode = os.getenv("DZEN_PUBLISH_MODE", "auto").lower()
        article = load_article(resolve_path(article_path(item) or "")) if article_path(item) else None
        use_sync = article and dzen_routing(format_for_dzen(article), mode)[0]
        if use_sync:
            if dzen_ch == main_ch and dzen_ch:
                raise SystemExit(
                    "TELEGRAM_DZEN_CHANNEL_ID и TELEGRAM_MAIN_CHANNEL_ID совпадают — "
                    "разделите каналы. См. docs/content-channels.md"
                )
            if not token or not dzen_ch:
                raise SystemExit("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_DZEN_CHANNEL_ID")
        publish_dzen_article(item, dry_run=dry_run, token=token, channel=dzen_ch)
        if not dry_run:
            save_queue(items)

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
    full = ROOT / path
    if not full.exists():
        return ""
    article = load_article(full)
    url = fetch_dzen_url_by_title(article.title)
    if url:
        item["dzen_url"] = url
        item["dzen_rss_pending"] = False
        save_queue(items)
        print(f"✓ dzen_url для {campaign_id}: {url}")
    return url


def wait_for_dzen_url(
    campaign_id: str,
    *,
    max_minutes: int | None = None,
    interval_sec: int | None = None,
) -> str:
    """Ожидание появления статьи в Дзене (RSS → API export)."""
    max_minutes = max_minutes if max_minutes is not None else int(os.getenv("DZEN_URL_POLL_MAX_MINUTES", "15"))
    interval_sec = interval_sec if interval_sec is not None else int(os.getenv("DZEN_URL_POLL_INTERVAL_SEC", "60"))
    deadline = time.time() + max(1, max_minutes) * 60
    while time.time() < deadline:
        url = sync_dzen_url(campaign_id)
        if url:
            return url
        remaining = int(deadline - time.time())
        if remaining <= 0:
            break
        sleep_for = min(interval_sec, remaining)
        print(f"  ↻ dzen_url: ждём {sleep_for}с (осталось ~{remaining // 60} мин)")
        time.sleep(sleep_for)
    return ""


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
            burst = int(os.getenv("DZEN_URL_POLL_BURST_MINUTES", "15"))
            url = wait_for_dzen_url(cid, max_minutes=burst)
            if not url:
                return False, f"dzen_url ещё нет — pending (автоповтор schedule)"
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


def _load_article_meta(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        return yaml.safe_load(raw.split("---", 2)[1]) or {}
    return {}


def cmd_dzen_rss_setup(args: argparse.Namespace) -> int:
    """Пересборка feed, деплой на blog.mkekspert.ru, проверка перед подключением в Студии."""
    from dzen_rss import (
        FEED_FILE,
        FEED_LINK,
        COVER_BASE,
        deploy_rss_public,
        rebuild_full_feed,
        validate_feed_for_dzen,
        verify_feed_public,
    )

    load_env()
    items = load_queue()
    path = rebuild_full_feed(
        items,
        article_to_html=article_to_dzen_html,
        load_meta=_load_article_meta,
    )
    print(f"✓ Лента: {path}")

    for item in items:
        rel = item.get("dzen_article")
        if rel:
            write_dzen_html_export(ROOT / rel, cover_rel=item.get("cover"))

    issues = validate_feed_for_dzen()
    if issues:
        print("\n⚠ Проверка ленты:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ Лента проходит проверки для Дзена")

    deployed = deploy_rss_public(campaign_id="rss-setup", dry_run=args.dry_run)
    for line in deployed:
        print(f"  Deploy: {line}")

    print(f"\nURL для Студии Дзена:\n  {FEED_LINK}")
    print(f"Обложки:\n  {COVER_BASE}/")

    if not args.dry_run and verify_feed_public(FEED_LINK):
        print("\n✓ Лента доступна — можно отправлять в Студии")
        print("  Студия → Настройки → Свой сайт → blog.mkekspert.ru → трансляция RSS")
    elif not args.dry_run:
        print("\n✗ Лента на blog.mkekspert.ru пока недоступна")
        print("  Настройте DNS + GitHub Pages: checklists/dzen-rss-tilda.md")
        print(f"  Ожидаемый URL: {FEED_LINK}")
        return 1
    return 0


def cmd_schedule_sync_urls(_args: argparse.Namespace) -> int:
    load_env()
    items = load_queue()
    n = 0
    for item in items:
        if item.get("dzen_url"):
            continue
        rel = article_path(item)
        if not rel or not (ROOT / rel).exists():
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
    cover = resolve_cover_path(item, vk=True) or ROOT / item["cover"]
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

    fmt_html = sub.add_parser("format-dzen-html", help="HTML для вставки в Студию Дзена")
    fmt_html.add_argument("article", help="путь от автоматизация-контента/")

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

    rss = sub.add_parser("dzen-rss", help="RSS для Дзена: сборка и деплой на mkekspert.ru")
    rss_sub = rss.add_subparsers(dest="dzen_rss_cmd", required=True)
    rss_setup = rss_sub.add_parser("setup", help="Пересобрать feed, задеплоить, вывести URL для Студии")
    rss_setup.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "cover":
        from generate_cover import ensure_cover_for_queue_id

        load_env()
        path = ensure_cover_for_queue_id(args.campaign_id, force=args.force)
        if not path:
            raise SystemExit("Не удалось сгенерировать обложку")
        print(path)
        return 0

    if args.command == "dzen-rss":
        if args.dzen_rss_cmd == "setup":
            return cmd_dzen_rss_setup(args)
        return 1

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

    if args.command == "format-dzen-html":
        path = resolve_path(args.article)
        out = write_dzen_html_export(path)
        print(out)
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
