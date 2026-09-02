#!/usr/bin/env python3
"""RSS-лента Дзена с HTML (content:encoded) — жирный, H2, обложка."""

from __future__ import annotations

import html
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = ROOT / "articles" / "dzen" / "feed.xml"
COVERS_DIR = ROOT / "assets" / "covers"
SITE_URL = os.getenv("DZEN_RSS_SITE_URL", "https://mkekspert.ru")


def _git_root() -> Path:
    p = ROOT
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return ROOT.parent
        p = p.parent


def _git_branch() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=_git_root(),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or "main"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.getenv("GITHUB_BRANCH", "main")


def _default_github_raw_base() -> str:
    repo = os.getenv("GITHUB_REPO", "mkdigitaly-pixel/test")
    branch = _git_branch()
    return f"https://raw.githubusercontent.com/{repo}/{branch}/автоматизация-контента"


FEED_LINK = os.getenv("DZEN_RSS_FEED_URL") or f"{SITE_URL.rstrip('/')}/dzen-feed.xml"
COVER_BASE = os.getenv("DZEN_COVER_BASE_URL") or f"{SITE_URL.rstrip('/')}/dzen-covers"
DZEN_CHANNEL_SLUG = os.getenv("DZEN_CHANNEL_SLUG", "klientyandtrafik")
MIN_FEED_ITEMS = int(os.getenv("DZEN_RSS_MIN_ITEMS", "10"))

# ЧПУ на mkekspert.ru (страницы из sitemap, не /blog/* — их нет на Tilda)
ARTICLE_SITE_LINKS: dict[str, str] = {
    "penoplast-case": "/press-forms",
    "7-errors-direct": "/portfolio",
    "no-leads-direct": "/razbor-direct",
    "autotarget-b2b": "/portfolio",
}


def rss_draft_mode() -> bool:
    """native-draft в RSS → черновик в Студии; без него — автопубликация."""
    return os.getenv("DZEN_RSS_DRAFT", "false").lower() in ("1", "true", "yes")


def deploy_feed_copy() -> Path | None:
    """Копия feed.xml на публичный путь (если задан DZEN_RSS_DEPLOY_PATH)."""
    dest_raw = os.getenv("DZEN_RSS_DEPLOY_PATH", "").strip()
    if not dest_raw or not FEED_FILE.exists():
        return None
    dest = Path(dest_raw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(FEED_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    return dest


def _cover_files_for_slug(slug: str) -> list[Path]:
    files: list[Path] = []
    for name in (f"{slug}.jpg", f"{slug}-vk.jpg"):
        path = COVERS_DIR / name
        if path.exists():
            files.append(path)
    return files


def deploy_feed_git(*, campaign_id: str = "", cover_rel: str | None = None, dry_run: bool = False) -> str:
    """Коммит и push feed.xml + обложек — публичный raw GitHub URL без Tilda."""
    if os.getenv("DZEN_RSS_DEPLOY_GIT", "true").lower() not in ("1", "true", "yes"):
        return ""
    if not FEED_FILE.exists():
        return ""

    git_root = _git_root()
    rel_feed = FEED_FILE.relative_to(git_root)
    paths: list[Path] = [rel_feed]

    slug = ""
    if cover_rel:
        slug = Path(cover_rel).stem.replace("-vk", "")
    elif campaign_id:
        slug = campaign_id
    if slug:
        for cover in _cover_files_for_slug(slug):
            paths.append(cover.relative_to(git_root))

    queue_file = ROOT / "queue" / "publish-queue.yaml"
    if queue_file.exists():
        paths.append(queue_file.relative_to(git_root))

    rel_paths = [str(p) for p in paths]
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--"] + rel_paths,
            cwd=git_root,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"⚠ git status: {exc}")
        return ""

    if not status:
        return f"git: без изменений ({FEED_LINK})"

    if dry_run:
        return f"[dry-run] git push: {', '.join(rel_paths)}"

    msg = f"deploy(dzen): {campaign_id or 'feed'}"
    try:
        subprocess.run(["git", "add", "--"] + rel_paths, cwd=git_root, check=True)
        subprocess.run(["git", "commit", "-m", msg], cwd=git_root, check=True)
        branch = _git_branch()
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=git_root, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"⚠ git deploy: {exc}")
        return ""
    return f"git push → {FEED_LINK}"


def verify_feed_public(url: str | None = None, *, retries: int = 3, delay_sec: float = 4.0) -> bool:
    """Проверка, что лента доступна по публичному URL после push."""
    import requests

    feed_url = url or FEED_LINK
    for attempt in range(retries):
        try:
            resp = requests.get(feed_url, headers={"User-Agent": "mkekspert-rss-check/1.0"}, timeout=30)
            if resp.status_code == 200 and "<rss" in resp.text[:500]:
                return True
        except requests.RequestException:
            pass
        if attempt + 1 < retries:
            time.sleep(delay_sec)
    return False


def deploy_rss_public(
    *,
    campaign_id: str = "",
    cover_rel: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Публикация RSS: SFTP на mkekspert.ru → локальная копия → git push."""
    results: list[str] = []
    sftp_msg = deploy_feed_sftp(dry_run=dry_run)
    if sftp_msg:
        results.append(sftp_msg)
    local = deploy_feed_copy()
    if local:
        results.append(f"local: {local}")
    git_msg = deploy_feed_git(campaign_id=campaign_id, cover_rel=cover_rel, dry_run=dry_run)
    if git_msg:
        results.append(git_msg)
    check_url = FEED_LINK
    if not dry_run and check_url:
        if verify_feed_public(check_url):
            results.append(f"feed OK: {check_url}")
        elif sftp_msg:
            results.append(f"deploy выполнен — проверьте {check_url}")
        elif "mkekspert.ru" in check_url:
            results.append(
                f"⚠ {check_url} ещё 404 — настройте DZEN_SFTP_* или DDOS-Guard proxy (см. checklists/dzen-rss-infra.md)"
            )
    return results


def article_site_link(campaign_id: str, slug: str) -> str:
    path = ARTICLE_SITE_LINKS.get(campaign_id, f"/portfolio")
    return f"{SITE_URL.rstrip('/')}{path}"


def fetch_dzen_channel_items(limit: int = 20) -> list[dict[str, Any]]:
    import requests

    try:
        resp = requests.get(
            f"https://dzen.ru/api/v3/launcher/export?channel_name={DZEN_CHANNEL_SLUG}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        resp.raise_for_status()
        return list(resp.json().get("items", []))[:limit]
    except Exception as exc:
        print(f"⚠ Dzen export API: {exc}")
        return []


def _text_to_html(text: str) -> str:
    parts = [f"<p>{html.escape(p.strip())}</p>" for p in text.split("\n") if p.strip()]
    return "\n".join(parts) if parts else "<p></p>"


def validate_feed_for_dzen(feed_path: Path | None = None) -> list[str]:
    """Проверка ленты перед отправкой в Студию. Пустой список = ок."""
    path = feed_path or FEED_FILE
    issues: list[str] = []
    if not path.exists():
        return ["feed.xml не найден"]
    raw = path.read_text(encoding="utf-8")
    items = re.findall(r"<item>.*?</item>", raw, re.DOTALL)
    if len(items) < MIN_FEED_ITEMS:
        issues.append(f"в ленте {len(items)} материалов — Дзен просит минимум {MIN_FEED_ITEMS} при первом подключении")
    if rss_draft_mode() and "native-draft" not in raw:
        issues.append("DZEN_RSS_DRAFT=true, но нет native-draft в ленте")
    if not rss_draft_mode() and "native-draft" in raw:
        issues.append("DZEN_RSS_DRAFT=false, но в ленте есть native-draft — пересоберите feed")
    feed_host = SITE_URL.replace("https://", "").replace("http://", "").rstrip("/")
    if FEED_LINK and feed_host not in FEED_LINK:
        issues.append(f"URL ленты {FEED_LINK} не на домене {feed_host} — Дзен отклонит")
    for item in items:
        if len(re.findall(r"<content:encoded>", item)) and len(item) < 400:
            issues.append("подозрительно короткий content:encoded в одном из item")
            break
    return issues


def deploy_feed_sftp(*, dry_run: bool = False) -> str:
    """Загрузка feed.xml и обложек на mkekspert.ru по SFTP."""
    host = os.getenv("DZEN_SFTP_HOST", "").strip()
    user = os.getenv("DZEN_SFTP_USER", "").strip()
    password = os.getenv("DZEN_SFTP_PASSWORD", "").strip()
    remote_feed = os.getenv("DZEN_SFTP_REMOTE_FEED", "/dzen-feed.xml").strip()
    remote_covers = os.getenv("DZEN_SFTP_REMOTE_COVERS", "/dzen-covers").strip()
    if not all([host, user, password]) or not FEED_FILE.exists():
        return ""
    if dry_run:
        return f"[dry-run] sftp {host}:{remote_feed}"

    import ftplib

    try:
        with ftplib.FTP(host, timeout=60) as ftp:
            ftp.login(user=user, passwd=password)
            with FEED_FILE.open("rb") as f:
                ftp.storbinary(f"STOR {remote_feed}", f)
            try:
                ftp.mkd(remote_covers)
            except ftplib.error_perm:
                pass
            ftp.cwd(remote_covers)
            for cover in COVERS_DIR.glob("*.jpg"):
                with cover.open("rb") as f:
                    ftp.storbinary(f"STOR {cover.name}", f)
    except Exception as exc:
        print(f"⚠ SFTP deploy: {exc}")
        return ""
    return f"sftp://{host}{remote_feed}"


def rebuild_full_feed(
    queue_items: list[dict[str, Any]],
    *,
    article_to_html: Any,
    load_meta: Any,
) -> Path:
    """Полная пересборка feed.xml из очереди + архив Дзена (до 10+ item)."""
    blocks: list[str] = []
    seen_guids: set[str] = set()

    for item in queue_items:
        rel = item.get("dzen_article")
        if not rel:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        meta = load_meta(path)
        title = str(meta.get("h1") or meta.get("title") or "").strip()
        description = str(meta.get("description") or title).strip()
        body_html = article_to_html(path)
        cid = str(item.get("id", ""))
        slug = _slug_from_path(path)
        guid = f"mkekspert-dzen-{cid}"
        if guid in seen_guids:
            continue
        seen_guids.add(guid)
        cover_rel = str(item.get("cover") or "")
        cover_url = cover_public_url(cover_rel or None)
        content = prepend_cover_html(body_html, cover_url)
        blocks.append(
            build_item_xml_str(
                guid=guid,
                title=title,
                link=article_site_link(cid, slug),
                pub_date=datetime.now(timezone.utc),
                description=description,
                content_html=content,
                cover_url=cover_url,
            )
        )

    if len(blocks) < MIN_FEED_ITEMS:
        archive_links = [
            "/portfolio",
            "/rotang",
            "/press-forms",
            "/urist",
            "/stomatologiya",
            "/lifts",
            "/razbor-direct",
        ]
        for idx, dzen_item in enumerate(fetch_dzen_channel_items(MIN_FEED_ITEMS * 2)):
            pub_id = str(dzen_item.get("publication_id") or dzen_item.get("id") or idx)
            guid = f"mkekspert-dzen-archive-{pub_id}"
            if guid in seen_guids:
                continue
            title = str(dzen_item.get("title") or "").strip()
            text = str(dzen_item.get("text") or "").strip()
            if not title or len(text) < 120:
                continue
            seen_guids.add(guid)
            link_path = archive_links[len(blocks) % len(archive_links)]
            blocks.append(
                build_item_xml_str(
                    guid=guid,
                    title=title,
                    link=f"{SITE_URL.rstrip('/')}{link_path}",
                    pub_date=datetime.now(timezone.utc),
                    description=text[:300],
                    content_html=_text_to_html(text),
                    cover_url="",
                )
            )
            if len(blocks) >= MIN_FEED_ITEMS:
                break

    xml = render_feed(blocks[:50])
    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEED_FILE.write_text(xml, encoding="utf-8")
    return FEED_FILE


def _slug_from_path(path: Path) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)


def cover_public_url(cover_rel: str | None) -> str:
    if not cover_rel:
        return ""
    return f"{COVER_BASE.rstrip('/')}/{Path(cover_rel).name}"


def prepend_cover_html(body_html: str, cover_url: str) -> str:
    if not cover_url or cover_url in body_html:
        return body_html
    figure = f'<figure><img src="{html.escape(cover_url, quote=True)}"/></figure>'
    return figure + "\n" + body_html


def _cdata(text: str) -> str:
    return f"<![CDATA[{text}]]>"


def build_item_xml_str(
    *,
    guid: str,
    title: str,
    link: str,
    pub_date: datetime,
    description: str,
    content_html: str,
    cover_url: str,
    draft: bool | None = None,
) -> str:
    if draft is None:
        draft = rss_draft_mode()
    desc = html.escape(description[:500])
    title_esc = html.escape(title)
    lines = [
        "    <item>",
        f"      <title>{title_esc}</title>",
        f"      <link>{html.escape(link)}</link>",
        f'      <guid isPermaLink="false">{html.escape(guid)}</guid>',
        f"      <pubDate>{pub_date.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>",
        f"      <description>{desc}</description>",
    ]
    if draft:
        lines.append("      <category>native-draft</category>")
    lines.extend(
        [
            "      <category>format-article</category>",
            "      <category>index</category>",
            "      <category>comment-none</category>",
        ]
    )
    if cover_url:
        lines.append(
            f'      <enclosure url="{html.escape(cover_url, quote=True)}" type="image/jpeg"/>'
        )
    lines.append(f"      <content:encoded>{_cdata(content_html)}</content:encoded>")
    lines.append('      <media:rating scheme="urn:simple">nonadult</media:rating>')
    lines.append("    </item>")
    return "\n".join(lines)


def render_feed(item_blocks: list[str], channel_title: str = "mkekspert — Дзен") -> str:
    items = "\n".join(item_blocks)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>{html.escape(channel_title)}</title>
    <link>{html.escape(SITE_URL)}</link>
    <language>ru</language>
{items}
  </channel>
</rss>
"""


def upsert_article_item(
    *,
    campaign_id: str,
    article_path: Path,
    title: str,
    description: str,
    body_html: str,
    cover_rel: str | None,
    pub_date: datetime | None = None,
) -> Path:
    slug = _slug_from_path(article_path)
    guid = f"mkekspert-dzen-{campaign_id}"
    link = article_site_link(campaign_id, slug)
    cover_url = cover_public_url(cover_rel)
    content = prepend_cover_html(body_html, cover_url)
    new_block = build_item_xml_str(
        guid=guid,
        title=title,
        link=link,
        pub_date=pub_date or datetime.now(timezone.utc),
        description=description,
        content_html=content,
        cover_url=cover_url,
    )

    existing_blocks: list[str] = []
    if FEED_FILE.exists():
        raw = FEED_FILE.read_text(encoding="utf-8")
        for block in re.findall(r"<item>.*?</item>", raw, re.DOTALL):
            if f"<guid isPermaLink=\"false\">{guid}</guid>" in block:
                continue
            existing_blocks.append(block)

    xml = render_feed([new_block] + existing_blocks[:49])
    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEED_FILE.write_text(xml, encoding="utf-8")
    return FEED_FILE
