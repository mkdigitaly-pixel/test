#!/usr/bin/env python3
"""RSS-лента Дзена с HTML (content:encoded) — жирный, H2, обложка."""

from __future__ import annotations

import html
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = ROOT / "articles" / "dzen" / "feed.xml"
COVERS_DIR = ROOT / "assets" / "covers"
SITE_URL = os.getenv("DZEN_RSS_SITE_URL", "https://blog.mkekspert.ru")


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
    """Публикация RSS: GitHub Pages (blog.mkekspert.ru) → git push ветки кода → SFTP (опц.)."""
    results: list[str] = []
    gh_msg = deploy_gh_pages(campaign_id=campaign_id, dry_run=dry_run)
    if not dry_run and os.getenv("DZEN_RSS_DEPLOY_GH_PAGES", "true").lower() in ("1", "true", "yes") and not gh_msg:
        raise RuntimeError("GitHub Pages: публикация не подтверждена")
    if gh_msg:
        results.append(gh_msg)
    git_msg = deploy_feed_git(campaign_id=campaign_id, cover_rel=cover_rel, dry_run=dry_run)
    if git_msg:
        results.append(git_msg)
    local = deploy_feed_copy()
    if local:
        results.append(f"local: {local}")
    if os.getenv("DZEN_RSS_DEPLOY_SFTP", "false").lower() in ("1", "true", "yes"):
        sftp_msg = deploy_feed_sftp(dry_run=dry_run)
        if sftp_msg:
            results.append(sftp_msg)
    check_url = FEED_LINK
    if not dry_run and check_url:
        if verify_feed_public(check_url):
            results.append(f"feed OK: {check_url}")
        elif gh_msg and "gh-pages" in gh_msg:
            results.append(
                f"deploy выполнен — DNS/GitHub Pages: checklists/dzen-rss-tilda.md → {check_url}"
            )
    return results


def article_site_link(campaign_id: str, slug: str = "") -> str:
    """Публичная страница статьи на blog.mkekspert.ru (ссылка из RSS для Дзена)."""
    return f"{SITE_URL.rstrip('/')}/articles/{campaign_id}.html"


def _parse_md_meta(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


_MONTHS_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _parse_item_datetime(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_pub_date_ru(raw: str) -> str:
    """2026-09-30 → «30 сентября 2026»."""
    parsed = _parse_item_datetime(raw)
    if not parsed:
        return ""
    # The editorial calendar uses Asia/Yekaterinburg (UTC+5).
    local = parsed.astimezone(timezone(timedelta(hours=5)))
    return f"{local.day} {_MONTHS_RU[local.month]} {local.year}"




def _verified_publication_date(raw: Any = "") -> str:
    """Actual publication date only: never infer it from a schedule or filename."""
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.date() > datetime.now(timezone.utc).date():
        return ""
    return text


def _rss_article_publication_dates() -> dict[str, str]:
    """Use the blog RSS date, independently of publication on other platforms."""
    if not FEED_FILE.is_file():
        return {}
    dates = {}
    root = ET.fromstring(FEED_FILE.read_bytes())
    for item in root.findall("./channel/item"):
        url = item.findtext("link", "")
        prefix = f"{SITE_URL.rstrip('/')}/articles/"
        if not url.startswith(prefix) or not url.endswith(".html"):
            continue
        cid = url[len(prefix):-5]
        if not re.fullmatch(r"[a-z0-9-]+", cid):
            continue
        try:
            parsed = parsedate_to_datetime(item.findtext("pubDate", ""))
            if parsed.tzinfo is None:
                continue
            date = _verified_publication_date(parsed.isoformat())
        except (TypeError, ValueError, OverflowError):
            continue
        if date:
            dates[cid] = date
    return dates


def _publication_time_html(raw: Any = "") -> str:
    date = _verified_publication_date(raw)
    if not date:
        return ""
    label = format_pub_date_ru(date)
    return f'<time class="post-date" datetime="{html.escape(date)}">{label}</time>'



def _item_pub_raw(item: dict[str, Any]) -> str:
    """Actual blog date, independently of a schedule or another platform."""
    known = _verified_publication_date(item.get("blog_published_at"))
    return known or _rss_article_publication_dates().get(str(item.get("id") or ""), "")


def _cover_urls(cover_rel: str) -> tuple[str, str]:
    """(landscape, square/vk) публичные URL обложек."""
    if not cover_rel:
        return "", ""
    landscape = cover_public_url(cover_rel)
    base = Path(cover_rel)
    vk_rel = str(base.with_name(f"{base.stem}-vk{base.suffix}"))
    vk_path = ROOT / vk_rel
    square = cover_public_url(vk_rel) if vk_path.is_file() else landscape
    return landscape, square


def _blog_post_meta(item: dict[str, Any]) -> dict[str, Any] | None:
    """Метаданные поста для блога и SEO (approved / published с текстом)."""
    cid = str(item.get("id") or "")
    rel = str(item.get("dzen_article") or "")
    status = str(item.get("status") or "")
    if not cid or not rel or status not in ("approved", "published"):
        return None
    art_path = ROOT / rel
    html_export = ROOT / "articles" / "dzen" / "html" / f"{art_path.stem}.html"
    if not art_path.is_file() and not html_export.is_file():
        return None
    meta = _parse_md_meta(art_path)
    title = str(meta.get("h1") or meta.get("title") or item.get("topic") or cid).strip()
    description = str(meta.get("description") or title).strip()
    cover_rel = str(item.get("cover") or "")
    cover_url, cover_square_url = _cover_urls(cover_rel)
    published_at = _item_pub_raw(item)
    return {
        "id": cid,
        "title": title,
        "description": description,
        "cover_url": cover_url,
        "cover_square_url": cover_square_url,
        "cover_name": Path(cover_rel).name if cover_rel else "",
        "url": article_site_link(cid),
        "status": status,
        "published_at": published_at,
        "modified_at": _verified_publication_date(item.get("blog_modified_at")),
        "published_label": format_pub_date_ru(published_at),
        "keyword": str(meta.get("main_keyword") or "").strip(),
    }


BLOG_CSS = (ROOT / "articles/dzen/blog-site/blog-theme.css").read_text(encoding="utf-8")
BLOG_STYLE_VERSION = hashlib.sha256(BLOG_CSS.encode("utf-8")).hexdigest()[:12]


BLOG_METRIKA_ID = os.getenv("DZEN_BLOG_METRIKA_ID", "97606312").strip()


def _metrika_snippet() -> str:
    """Счётчик Метрики основного сайта — один на mkekspert.ru и blog."""
    if not BLOG_METRIKA_ID:
        return ""
    cid = html.escape(BLOG_METRIKA_ID, quote=True)
    return f"""<!-- Yandex.Metrika counter -->
<script type="text/javascript">
(function(m,e,t,r,i,k,a){{
m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};
m[i].l=1*new Date();
for (var j = 0; j < document.scripts.length; j++) {{if (document.scripts[j].src === r) {{ return; }}}}
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)
}})(window, document,'script','https://mc.yandex.ru/metrika/tag.js', 'ym');
ym({BLOG_METRIKA_ID}, 'init', {{webvisor:true, clickmap:true, referrer: document.referrer, url: location.href, accurateTrackBounce:true, trackLinks:true}});
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/{cid}" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
<!-- /Yandex.Metrika counter -->
"""


def _site_chrome(inner: str, *, title: str, description: str, canonical: str, extra_head: str = "", og_type: str = "website") -> str:
    zen = os.getenv("DZEN_ZEN_VERIFICATION", "").strip()
    yandex = os.getenv("DZEN_YANDEX_VERIFICATION", "").strip()
    metas = ""
    if zen:
        metas += f'<meta name="zen-verification" content="{html.escape(zen)}" />\n'
    if yandex:
        metas += f'<meta name="yandex-verification" content="{html.escape(yandex)}" />\n'
    metrika = _metrika_snippet()
    template_dir = ROOT / "automation" / "templates"
    header = (template_dir / "blog-header.html").read_text(encoding="utf-8")
    footer = (template_dir / "blog-footer.html").read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{metas}<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:site_name" content="МК Эксперт">
<meta property="og:url" content="{html.escape(canonical)}">
<meta property="og:type" content="{html.escape(og_type)}">
<link rel="canonical" href="{html.escape(canonical)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="120x120" href="/favicon-120.png">
<link rel="apple-touch-icon" href="/favicon-120.png">
<link rel="alternate" type="application/rss+xml" title="МК Эксперт — RSS" href="/dzen-feed.xml">
{extra_head}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog-theme.css?v={BLOG_STYLE_VERSION}">
{metrika}</head>
<body>
{header}
{inner}
{footer}
</body>
</html>
"""



ARTICLE_RELATED_LINKS = {
    'no-leads-direct': [('/audit-yandex-direct', 'Аудит рекламы и аналитики'), ('/vedenie-yandex-direct', 'Ведение и оптимизация кампаний'), ('https://blog.mkekspert.ru/articles/metrika-goals.html', 'Как проверить цели Метрики')],
    '7-errors-direct': [('/audit-yandex-direct', 'Аудит Яндекс Директа'), ('https://blog.mkekspert.ru/articles/no-leads-direct.html', 'Почему реклама не приносит заявки')],
    'audit-direct': [('/audit-yandex-direct', 'Заказать аудит Яндекс Директа'), ('https://blog.mkekspert.ru/articles/7-errors-direct.html', 'Типичные ошибки в рекламных кампаниях')],
    'penoplast-case': [('/yandex-direct-dlya-b2b', 'Реклама для B2B и производства'), ('/keys-ppu', 'Кейс рекламы промышленного оборудования')],
    'autotarget-b2b': [('/yandex-direct-dlya-b2b', 'Яндекс Директ для B2B'), ('/vedenie-yandex-direct', 'Оптимизация действующих кампаний')],
    'metrika-goals': [('/nastrojka-yandex-direct', 'Настройка рекламы с аналитикой'), ('/audit-yandex-direct', 'Аудит кампаний и целей Метрики')],
    'epk-leads': [('/nastrojka-yandex-direct', 'Настройка Яндекс Директа для бизнеса'), ('/vedenie-yandex-direct', 'Ведение и оптимизация рекламы')],
    'rsa-vs-search': [('/nastrojka-yandex-direct', 'Подготовка и запуск рекламы'), ('/vedenie-yandex-direct', 'Проверка запросов и площадок')],
    'budget-waste': [('/audit-yandex-direct', 'Проверка причин расхода бюджета'), ('/vedenie-yandex-direct', 'Сопровождение и оптимизация рекламы')],
    'choose-directologist': [('/nastrojka-yandex-direct', 'Что входит в настройку рекламы'), ('/portfolio', 'Кейсы Яндекс Директа')],
    'landing-conversion': [('/nastrojka-yandex-direct', 'Подготовка рекламы и посадочной страницы'), ('/keys-ppu', 'Кейс: реклама и посадочная страница для производства')],
    'negative-keywords': [('/vedenie-yandex-direct', 'Оптимизация запросов и кампаний'), ('https://blog.mkekspert.ru/articles/7-errors-direct.html', 'Ошибки, которые мешают рекламе')],
    'leads-without-sales': [('/audit-yandex-direct', 'Аудит рекламы и аналитики'), ('/vedenie-yandex-direct', 'Оптимизация рекламы по обращениям')],
    'direct-price': [('/nastrojka-yandex-direct', 'Стоимость и состав настройки рекламы'), ('/vedenie-yandex-direct', 'Стоимость ведения Яндекс Директа')],
}


def _article_related_html(campaign_id: str) -> str:
    links = ARTICLE_RELATED_LINKS.get(campaign_id, [
        ('/audit-yandex-direct', 'Аудит рекламы и аналитики'),
        ('/nastrojka-yandex-direct', 'Настройка Яндекс Директа для бизнеса'),
    ])
    items = []
    for target, label in links:
        url = 'https://mkekspert.ru' + target if target.startswith('/') else target
        items.append(f'<li><a href="{html.escape(url)}">{html.escape(label)}</a></li>')
    return ('<section class="cta seo-related" aria-label="Услуги и статьи по теме">'
            '<h2>Продолжить по теме</h2><ul>' + ''.join(items) + '</ul></section>')


def _article_html_page(campaign_id: str, body_html: str, post: dict[str, Any] | None = None) -> str:
    """Полная HTML-страница статьи для GitHub Pages (SEO + обложка)."""
    post = post or {}
    link = article_site_link(campaign_id)
    title = str(post.get("title") or "")
    if not title:
        title_m = re.search(r"<h1>(.*?)</h1>", body_html, re.DOTALL)
        title = html.unescape(re.sub(r"<[^>]+>", "", title_m.group(1))) if title_m else campaign_id
    description = str(post.get("description") or title).strip()
    cover_url = str(post.get("cover_url") or "")
    # убрать дубль обложки из тела, если покажем её отдельно
    body = body_html
    if cover_url:
        body = re.sub(
            r"<figure>\s*<img[^>]*src=\"[^\"]*\"[^>]*/?>\s*</figure>\s*",
            "",
            body,
            count=1,
        )
    cover_square = str(post.get("cover_square_url") or cover_url)
    if cover_url:
        sources = ""
        if cover_square and cover_square != cover_url:
            sources = (
                f'<source media="(max-width: 640px)" '
                f'srcset="{html.escape(cover_square)}" type="image/jpeg">'
            )
        cover_block = (
            f'<figure class="cover-wrap"><picture>{sources}'
            f'<img class="cover" src="{html.escape(cover_url)}" '
            f'alt="{html.escape(title)}" width="1200" height="675" '
            f'decoding="async" '
            f'sizes="(max-width: 720px) 100vw, 720px">'
            f"</picture></figure>"
        )
    else:
        cover_block = ""
    published_label = str(post.get("published_label") or "").strip()
    published_iso = _verified_publication_date(post.get("published_at"))
    if published_label and published_iso:
        date_html = f'<p class="publication-date">Опубликовано: <time datetime="{html.escape(published_iso)}">{html.escape(published_label)}</time></p>'
        body = re.sub(r'(<h1\b[^>]*>.*?</h1>)', lambda m: m.group(1) + '\n' + date_html, body, count=1, flags=re.DOTALL)
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "mainEntityOfPage": link,
        "author": {"@type": "Person", "@id": "https://mkekspert.ru/#maria", "name": "Мария Ковалева", "url": "https://mkekspert.ru/#about"},
        "publisher": {
            "@type": "Organization",
            "@id": "https://mkekspert.ru/#organization",
            "name": "МК Эксперт",
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL.rstrip('/')}/favicon-120.png"},
        },
        "inLanguage": "ru-RU",
    }
    if cover_url:
        schema["image"] = [cover_url]
        if cover_square and cover_square != cover_url:
            schema["image"].append(cover_square)
    if published_iso:
        schema["datePublished"] = published_iso
    og_image = f'<meta property="og:image" content="{html.escape(cover_url)}">\n' if cover_url else ""
    if published_iso:
        og_image += f'<meta property="article:published_time" content="{html.escape(published_iso)}">\n'
    modified = _verified_publication_date(post.get("modified_at"))
    if modified:
        schema["dateModified"] = modified
    breadcrumbs = {
        "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": "https://mkekspert.ru/"},
            {"@type": "ListItem", "position": 2, "name": "Блог", "item": SITE_URL.rstrip("/") + "/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": link},
        ],
    }
    graph = {"@context": "https://schema.org", "@graph": [schema, breadcrumbs]}
    schema_json = json.dumps(graph, ensure_ascii=False).replace("<", "\\u003c")
    extra = og_image + f'<script type="application/ld+json">{schema_json}</script>\n' 
    inner = f"""
<main class="site article-wrap">
{cover_block}
<p class="meta-line"><a href="/">← Все статьи</a> · Яндекс Директ · B2B</p>
<article>
{body}
</article>
{_article_related_html(campaign_id)}
<p class="cta">
<a href="https://mkekspert.ru/razbor-direct?utm_source=blog&utm_medium=article&utm_campaign={html.escape(campaign_id)}">Бесплатный разбор Директа</a>
· <a href="https://mkekspert.ru">mkekspert.ru</a>
· <a href="https://t.me/Mariya1740">Telegram</a>
</p>
</main>
"""
    return _site_chrome(
        inner,
        title=f"{title} — МК Эксперт",
        description=description,
        canonical=link,
        extra_head=extra,
        og_type="article",
    )



def _queue_items() -> list[dict[str, Any]]:
    queue_file = ROOT / "queue" / "publish-queue.yaml"
    if not queue_file.is_file():
        return []
    data = yaml.safe_load(queue_file.read_text(encoding="utf-8")) or {}
    return list(data.get("items") or [])


def _article_body_html(item: dict[str, Any]) -> str:
    """HTML тела статьи: готовый export или генерация из markdown."""
    rel = str(item.get("dzen_article") or "")
    if not rel:
        return ""
    art_path = ROOT / rel
    html_export = ROOT / "articles" / "dzen" / "html" / f"{art_path.stem}.html"
    if html_export.is_file():
        body = html_export.read_text(encoding="utf-8")
    elif art_path.is_file():
        from publish import article_to_dzen_html

        body = article_to_dzen_html(art_path)
        cover_rel = str(item.get("cover") or "")
        if cover_rel:
            body = prepend_cover_html(body, cover_public_url(cover_rel))
    else:
        return ""
    return body.replace(
        "https://mkekspert.ru/dzen-covers/",
        f"{COVER_BASE.rstrip('/')}/",
    )


BLOG_SITE_DIR = ROOT / "articles" / "dzen" / "blog-site"


def _blog_posts(campaign_id: str = "") -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _queue_items():
        if item.get("status") != "published" and item.get("id") != campaign_id:
            continue
        post = _blog_post_meta(item)
        if not post or post["id"] in seen:
            continue
        seen.add(post["id"])
        posts.append(post)
    # newest first; published before approved drafts
    def _sort_key(p: dict[str, Any]) -> tuple[Any, ...]:
        dt = _parse_item_datetime(str(p.get("published_at") or "")) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        return (0 if p["status"] == "published" else 1, -dt.timestamp(), p["title"])

    posts.sort(key=_sort_key)
    return posts


def _blog_index_html(posts: list[dict[str, Any]] | None = None) -> str:
    """Главная blog.mkekspert.ru — лента статей с обложками (SEO + Дзен)."""
    site = SITE_URL.rstrip("/")
    posts = _blog_posts() if posts is None else posts
    cards = []
    for p in posts:
        if p["cover_url"]:
            square = p.get("cover_square_url") or p["cover_url"]
            sources = ""
            if square and square != p["cover_url"]:
                sources = (
                    f'<source media="(max-width: 640px)" '
                    f'srcset="{html.escape(square)}" type="image/jpeg">'
                )
            img = (
                f'<div class="post-media"><picture>{sources}'
                f'<img src="{html.escape(p["cover_url"])}" alt="{html.escape(p["title"], quote=True)}" loading="lazy" '
                f'decoding="async" width="640" height="400" '
                f'sizes="(max-width: 640px) 100vw, 320px">'
                f"</picture></div>"
            )
        else:
            img = ""
        date_html = (
            f'<span class="post-date"><time datetime="{html.escape(str(p.get("published_at") or "")[:10])}">'
            f'{html.escape(p["published_label"])}</time></span>'
            if p.get("published_label")
            else ""
        )
        cards.append(
            f'<a class="post" href="/articles/{html.escape(p["id"])}.html">'
            f"{img}"
            f'<div class="post-body">{date_html}<h2>{html.escape(p["title"])}</h2>'
            f'<p>{html.escape(p["description"][:180])}{"…" if len(p["description"]) > 180 else ""}</p>'
            '<div class="post-more">Читать статью <span aria-hidden="true">↗</span></div>'
            f"</div></a>"
        )
    grid = "\n".join(cards) if cards else "<p>Статьи появятся после публикации.</p>"
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": p["url"],
                "name": p["title"],
            }
            for i, p in enumerate(posts)
        ],
    }
    org = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{site}/#organization",
                "name": "МК Эксперт",
                "url": "https://mkekspert.ru",
                "logo": f"{site}/favicon-120.png",
                "sameAs": [
                    "https://dzen.ru/klientyandtrafik",
                    "https://t.me/mariyaprodirect",
                    "https://vk.ru/klientyandtrafik",
                ],
            },
            {
                "@type": "Blog",
                "@id": f"{site}/#blog",
                "name": "МК Эксперт — блог",
                "url": site,
                "description": "Кейсы и разборы Яндекс Директа для B2B",
                "publisher": {"@id": f"{site}/#organization"},
                "inLanguage": "ru-RU",
            },
            item_list,
        ],
    }
    extra = f'<script type="application/ld+json">{json.dumps(org, ensure_ascii=False)}</script>\n'
    inner = f"""
<main class="site">
<section class="hero">
<p class="eyebrow">Блог · Яндекс Директ</p>
<h1>Блог о <span>Яндекс Директе</span> для B2B</h1>
<p>Кейсы с цифрами, разборы кабинета и практика — то, что реально двигает заявки.</p>
<a class="hero-cta" href="https://mkekspert.ru/razbor-direct?utm_source=blog&utm_medium=index&utm_campaign=home">Бесплатный разбор Директа</a>
</section>
<p class="section-label">Статьи и разборы</p>
<section class="grid" aria-label="Статьи">
{grid}
</section>
<p class="cta">Нужен разбор кабинета? <a href="https://mkekspert.ru/razbor-direct?utm_source=blog&utm_medium=index&utm_campaign=home">Записаться на бесплатный разбор</a></p>
</main>
"""
    return _site_chrome(
        inner,
        title="МК Эксперт — блог о Яндекс Директе",
        description="Кейсы и разборы Яндекс Директа для B2B: CPL, заявки, Метрика. Мария Ковалева, mkekspert.ru",
        canonical=f"{site}/",
        extra_head=extra,
    )



def _sitemap_lastmod(raw: str = "") -> str:
    """Дата для <lastmod> в формате YYYY-MM-DD (Яндекс Вебмастер)."""
    text = _verified_publication_date(raw)
    if text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""



def _blog_contacts_html() -> str:
    """Страница контактов/географии — URL для модерации региона в Вебмастере."""
    site = SITE_URL.rstrip("/")
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": "МК Эксперт",
        "url": "https://mkekspert.ru",
        "description": "Ведение и аудит Яндекс Директа для B2B",
        "areaServed": [
            {"@type": "Country", "name": "Россия"},
            {"@type": "City", "name": "Москва"},
            {"@type": "City", "name": "Санкт-Петербург"},
        ],
        "founder": {"@type": "Person", "name": "Мария Ковалева"},
        "sameAs": [
            "https://dzen.ru/klientyandtrafik",
            "https://t.me/mariyaprodirect",
            "https://vk.ru/klientyandtrafik",
        ],
    }
    extra = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>\n'
    inner = f"""
<main class="site">
<section class="hero">
<p class="eyebrow">Контакты · география</p>
<h1>Где работаем</h1>
<p>Блог МК Эксперт — часть сайта mkekspert.ru. Разборы и ведение Яндекс Директа для B2B.</p>
</section>
<div class="contacts-card" id="geo">
<h2>Регион обслуживания</h2>
<p>Работаю с компаниями <strong>по всей России</strong> онлайн. Формат работы можно обсудить в Telegram.</p>
<ul>
<li><strong>Регион обслуживания:</strong> Россия, онлайн</li>
<li><strong>Сайт:</strong> <a href="https://mkekspert.ru">mkekspert.ru</a></li>
<li><strong>Разбор Директа:</strong> <a href="https://mkekspert.ru/razbor-direct">mkekspert.ru/razbor-direct</a></li>
<li><strong>Telegram:</strong> <a href="https://t.me/Mariya1740">@Mariya1740</a> · канал <a href="https://t.me/mariyaprodirect">@mariyaprodirect</a></li>
<li><strong>Дзен:</strong> <a href="https://dzen.ru/klientyandtrafik">klientyandtrafik</a></li>
</ul>
</div>
<p><a class="hero-cta" href="https://mkekspert.ru/razbor-direct?utm_source=blog&utm_medium=contacts&utm_campaign=geo">Записаться на разбор</a></p>
</main>
"""
    return _site_chrome(
        inner,
        title="Контакты и регион — МК Эксперт",
        description="МК Эксперт: Москва, Санкт-Петербург и регионы России. Контакты Марии Ковалевой, разбор Яндекс Директа для B2B.",
        canonical=f"{site}/contacts.html",
        extra_head=extra,
    )



def _blog_sitemap_xml(posts: list[dict[str, Any]]) -> str:
    """Sitemap блога для Вебмастера: https://blog.mkekspert.ru/sitemap.xml"""
    site = SITE_URL.rstrip("/")
    newest = ""
    for p in posts:
        cand = str(p.get("published_at") or "")
        if cand and cand > newest:
            newest = cand
    home_mod = _sitemap_lastmod(newest)
    entries: list[tuple[str, str, str]] = [
        (f"{site}/", home_mod, "1.0"),
        (f"{site}/contacts.html", "", "0.6"),
    ]
    for p in posts:
        entries.append(
            (
                str(p["url"]),
                _sitemap_lastmod(str(p.get("modified_at") or p.get("published_at") or "")),
                "0.8",
            )
        )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod, priority in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(loc)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"



def _collect_gh_pages_files(campaign_id: str = "") -> dict[str, bytes]:
    """Файлы для ветки gh-pages: блог, feed, covers, SEO."""
    files: dict[str, bytes] = {}
    if FEED_FILE.is_file():
        files["dzen-feed.xml"] = FEED_FILE.read_bytes()
    files["CNAME"] = b"blog.mkekspert.ru\n"
    files[".nojekyll"] = b""
    files["robots.txt"] = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /dzen-feed.xml\n"
        "Sitemap: https://blog.mkekspert.ru/sitemap.xml\n"
    ).encode()
    posts = _blog_posts(campaign_id)
    files["index.html"] = _blog_index_html(posts).encode("utf-8")
    files["contacts.html"] = _blog_contacts_html().encode("utf-8")
    files["sitemap.xml"] = _blog_sitemap_xml(posts).encode("utf-8")
    if BLOG_SITE_DIR.is_dir():
        for path in BLOG_SITE_DIR.rglob("*"):
            if not path.is_file() or path.name.startswith("."):
                continue
            rel = path.relative_to(BLOG_SITE_DIR).as_posix()
            if rel in {"index.html", "contacts.html", "sitemap.xml", "robots.txt", "CNAME"}:
                continue
            files[rel] = path.read_bytes()
    if COVERS_DIR.is_dir():
        for cover in COVERS_DIR.glob("*.jpg"):
            files[f"covers/{cover.name}"] = cover.read_bytes()
            files[f"dzen-covers/{cover.name}"] = files[f"covers/{cover.name}"]
    for item in _queue_items():
        if item.get("status") != "published" and item.get("id") != campaign_id:
            continue
        post = _blog_post_meta(item)
        if not post:
            continue
        body = _article_body_html(item)
        if not body:
            continue
        files[f"articles/{post['id']}.html"] = _article_html_page(
            post["id"], body, post
        ).encode("utf-8")
    return files


def _with_publication_date(page: str, published_iso: str) -> str:
    """Add the known publication date while preserving the reviewed article layout."""
    label = format_pub_date_ru(published_iso)
    if not label or not re.search(r'<h1\b', page):
        return page
    page = re.sub(r'\s*<p class="publication-date">.*?</p>\s*', '', page, flags=re.DOTALL)
    page = re.sub(r'(<p class="meta-line">.*?)(?: · <time\b[^>]*>.*?</time>)(.*?</p>)', r'\1\2', page, flags=re.DOTALL)
    date_html = f'<p class="publication-date">Опубликовано: <time datetime="{html.escape(published_iso)}">{html.escape(label)}</time></p>'
    page = re.sub(r'(<h1\b[^>]*>.*?</h1>)', lambda m: m.group(1) + '\n' + date_html + '\n', page, count=1, flags=re.DOTALL)
    def schema_date(match):
        try:
            data = json.loads(match.group(1))
        except ValueError:
            return match.group(0)
        if isinstance(data, dict) and data.get('@type') == 'Article':
            data['datePublished'] = published_iso
            return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'
        return match.group(0)
    page = re.sub(r'<script type="application/ld\+json">(.*?)</script>', schema_date, page, flags=re.DOTALL)
    meta = f'<meta property="article:published_time" content="{html.escape(published_iso)}">'
    if re.search(r'<meta property="article:published_time"[^>]*>', page):
        page = re.sub(r'<meta property="article:published_time"[^>]*>', lambda m: meta, page)
    else:
        page = page.replace('</head>', meta + '\n</head>', 1)
    return page


def _page_publication_date(page: str) -> str:
    for raw in re.findall(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.DOTALL):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("@type") in ("Article", "BlogPosting"):
                return _verified_publication_date(node.get("datePublished"))
    return ""


def _write_gh_pages_files(worktree: Path, files: dict[str, bytes], campaign_id: str = "") -> None:
    posts = {p['id']: p for p in _blog_posts(campaign_id)}
    for rel_path, content in files.items():
        dest = worktree / rel_path
        if rel_path.startswith("articles/") and dest.exists() and rel_path != f"articles/{campaign_id}.html":
            post = posts.get(Path(rel_path).stem)
            if not post or not post.get('published_at'):
                continue
            existing = dest.read_text(encoding="utf-8")
            if _page_publication_date(existing) == post["published_at"] and 'class="publication-date"' in existing:
                continue
            content = _with_publication_date(existing,post['published_at']).encode('utf-8')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)


def deploy_gh_pages(*, campaign_id: str = "", dry_run: bool = False) -> str:
    """Деплой на GitHub Pages (ветка gh-pages) → blog.mkekspert.ru."""
    if os.getenv("DZEN_RSS_DEPLOY_GH_PAGES", "true").lower() not in ("1", "true", "yes"):
        return ""
    files = _collect_gh_pages_files(campaign_id)
    if not files:
        return "gh-pages: нет файлов для деплоя"

    git_root = _git_root()
    if not (git_root / ".git").exists():
        raise ValueError("Blog deployment requires a Git checkout")
    worktree = Path(tempfile.mkdtemp(prefix="mkekspert-blog-"))
    label = campaign_id or "blog"

    try:
        subprocess.run(["git", "fetch", "origin"], cwd=git_root, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    remote_check = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", "gh-pages"],
        cwd=git_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    branch_exists = bool(remote_check.stdout.strip())

    try:
        if branch_exists:
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree), "origin/gh-pages"],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "checkout", "-B", "gh-pages"],
                cwd=worktree,
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            subprocess.run(
                ["git", "worktree", "add", "--orphan", "-b", "gh-pages", str(worktree)],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
            )
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"⚠ gh-pages worktree: {err}")
        return ""

    _write_gh_pages_files(worktree, files, campaign_id)

    if dry_run:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=git_root,
            capture_output=True,
        )
        return f"[dry-run] gh-pages: {len(files)} файлов → {FEED_LINK}"

    subprocess.run(["git", "add", "-A"], cwd=worktree, check=True)
    status = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=worktree,
        text=True,
    ).strip()
    if not status:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=git_root,
            capture_output=True,
        )
        return f"gh-pages: без изменений ({FEED_LINK})"

    subprocess.run(
        ["git", "commit", "-m", f"deploy(blog): {label}"],
        cwd=worktree,
        check=True,
    )
    push = subprocess.run(
        ["git", "push", "-u", "origin", "HEAD:gh-pages"],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    if push.returncode != 0:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=git_root, capture_output=True)
        raise RuntimeError("GitHub Pages: push отклонён; повторить после проверки свежей ветки")
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(worktree)],
        cwd=git_root,
        capture_output=True,
    )
    return f"gh-pages → {FEED_LINK} ({len(files)} файлов)"


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
    if any("mkekspert-dzen-archive-" in item for item in items):
        issues.append("в ленте копии публикаций канала — Дзен отклоняет как дублированный контент")
    channel_titles = [str(it.get("title") or "") for it in fetch_dzen_channel_items(30)]
    for item in items:
        title_m = re.search(r"<title>(.*?)</title>", item)
        title = html.unescape(title_m.group(1)) if title_m else ""
        if title and _title_is_seen(title, channel_titles):
            issues.append(f"заголовок уже есть в канале Дзена — дубль: {title}")
            break
    for item in items:
        link_m = re.search(r"<link>(.*?)</link>", item)
        link = html.unescape(link_m.group(1)) if link_m else ""
        if link and "/articles/" not in link:
            issues.append(f"ссылка item не на статью блога: {link}")
            break
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


def _norm_title(title: str) -> str:
    text = (title or "").lower().replace("ё", "е")
    text = re.sub(r"[^a-zа-я0-9]+", " ", text)
    return " ".join(text.split())


def _titles_overlap(a: str, b: str) -> bool:
    """Дубль для Дзена — тот же или почти тот же заголовок, не общее «Директ B2B»."""
    na, nb = _norm_title(a), _norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) >= 40 and (na in nb or nb in na):
        return True
    return False


def _title_is_seen(title: str, seen: list[str]) -> bool:
    return any(_titles_overlap(title, prev) for prev in seen)


def _queue_article_titles(queue_items: list[dict[str, Any]] | None = None) -> list[str]:
    titles: list[str] = []
    for item in queue_items or _queue_items():
        rel = item.get("dzen_article")
        if not rel:
            continue
        meta = _parse_md_meta(ROOT / str(rel))
        title = str(meta.get("h1") or meta.get("title") or item.get("topic") or "").strip()
        if title:
            titles.append(title)
    return titles


def _parse_item_pub_date(item: dict[str, Any]) -> datetime:
    actual = _parse_item_datetime(_item_pub_raw(item))
    if actual is None:
        raise ValueError("RSS article has no verified publication date")
    return actual


def unique_archive_fill(existing_titles: list[str], needed: int) -> list[dict[str, Any]]:
    """Больше не добираем ленту копиями канала: Дзен отклоняет это как дубли."""
    return []


def _archive_page_html(pad: dict[str, Any]) -> str:
    title = str(pad.get("title") or "")
    description = str(pad.get("description") or title)
    body = str(pad.get("body_html") or "")
    url = str(pad.get("link") or article_site_link(str(pad.get("page_id") or "")))
    inner = (
        f'<article class="article-wrap"><h1>{html.escape(title)}</h1>'
        f'<p class="meta-line">Архив канала</p>{body}</article>'
    )
    return _site_chrome(
        inner,
        title=title,
        description=description,
        canonical=url,
        extra_head='<meta name="robots" content="noindex,nofollow">\n',
    )


def _item_eligible_for_rss(item: dict[str, Any], *, channel_titles: list[str] | None = None) -> bool:
    """Published — в ленте всегда. Approved — только если ещё нет в канале (не заранее)."""
    if not item.get("dzen_article"):
        return False
    status = str(item.get("status") or "")
    path = ROOT / str(item["dzen_article"])
    if not path.is_file():
        return False
    if status == "published":
        return bool(_item_pub_raw(item))
    if status != "approved":
        return False
    # An approval does not prove a publication date.
    if not _item_pub_raw(item):
        return False
    # будущие approved не кладём заранее — иначе Дзен забирает всё сразу
    if str(item.get("dzen_url") or "").strip():
        return False
    if channel_titles is None:
        return True
    try:
        from publish import parse_frontmatter

        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        title = str(meta.get("h1") or meta.get("title") or "").strip()
    except Exception:
        title = ""
    if title and _title_is_seen(title, channel_titles):
        return False
    return True


def rebuild_full_feed(
    queue_items: list[dict[str, Any]],
    *,
    article_to_html: Any,
    load_meta: Any,
) -> Path:
    """Пересборка feed.xml: published + новые approved, без будущих дублей канала."""
    blocks: list[str] = []
    seen_guids: set[str] = set()
    seen_titles: list[str] = []
    channel_titles = [str(it.get("title") or "") for it in fetch_dzen_channel_items(30)]

    ready = [
        item
        for item in queue_items
        if _item_eligible_for_rss(item, channel_titles=channel_titles)
    ]
    ready.sort(
        key=lambda item: (
            0 if str(item.get("status")) == "published" else 1,
            str(item.get("dzen_published_at") or item.get("published_at") or ""),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )

    for item in ready:
        rel = item.get("dzen_article")
        path = ROOT / str(rel)
        if not path.exists():
            continue
        meta = load_meta(path)
        title = str(meta.get("h1") or meta.get("title") or "").strip()
        description = str(meta.get("description") or title).strip()
        body_html = article_to_html(path)
        cid = str(item.get("id", ""))
        slug = _slug_from_path(path)
        guid = f"mkekspert-dzen-{cid}"
        if guid in seen_guids or not title:
            continue
        if _title_is_seen(title, seen_titles):
            continue
        # approved-новые — не дублировать канал; published оставляем (обновление текста)
        if str(item.get("status")) != "published" and _title_is_seen(title, channel_titles):
            continue
        seen_guids.add(guid)
        seen_titles.append(title)
        cover_rel = str(item.get("cover") or "")
        cover_url = cover_public_url(cover_rel or None)
        content = prepend_cover_html(body_html, cover_url)
        blocks.append(
            build_item_xml_str(
                guid=guid,
                title=title,
                link=article_site_link(cid, slug),
                pub_date=_parse_item_pub_date(item),
                description=description,
                content_html=content,
                cover_url=cover_url,
            )
        )

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
    built = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:media="http://search.yahoo.com/mrss/"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{html.escape(channel_title)}</title>
    <link>{html.escape(SITE_URL)}</link>
    <language>ru</language>
    <lastBuildDate>{built}</lastBuildDate>
    <atom:link href="{html.escape(FEED_LINK)}" rel="self" type="application/rss+xml"/>
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
        pub_date=pub_date or _parse_item_datetime(_item_pub_raw(next((i for i in _queue_items() if i.get("id") == campaign_id), {"id": campaign_id}))) or datetime.now(timezone.utc),
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
