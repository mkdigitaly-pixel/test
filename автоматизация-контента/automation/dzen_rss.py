#!/usr/bin/env python3
"""RSS-лента Дзена с HTML (content:encoded) — жирный, H2, обложка."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
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

# Архивные item из API Дзена — ссылки на основной сайт (Tilda)
ARCHIVE_SITE_LINKS: list[str] = [
    "/portfolio",
    "/rotang",
    "/press-forms",
    "/urist",
    "/stomatologiya",
    "/lifts",
    "/razbor-direct",
]


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
    return {
        "id": cid,
        "title": title,
        "description": description,
        "cover_url": cover_public_url(cover_rel) if cover_rel else "",
        "cover_name": Path(cover_rel).name if cover_rel else "",
        "url": article_site_link(cid),
        "status": status,
        "published_at": str(item.get("published_at") or item.get("scheduled_dzen") or ""),
        "keyword": str(meta.get("main_keyword") or "").strip(),
    }


BLOG_CSS = """
:root{--ink:#141414;--muted:#5a5a5a;--accent:#1a7a3a;--line:#e5e5e0;--paper:#fff}
*{box-sizing:border-box}
body{margin:0;font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;background:#f3f1eb;color:var(--ink);line-height:1.55}
a{color:#1d4ed8;text-underline-offset:3px}
.site{max-width:960px;margin:0 auto;padding:1.5rem 1.25rem 4rem}
.top{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:0.75rem 1.5rem;margin-bottom:2rem;padding-bottom:1rem;border-bottom:1px solid var(--line);font-family:system-ui,sans-serif}
.brand{font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);font-weight:700;text-decoration:none}
.nav{display:flex;flex-wrap:wrap;gap:0.85rem 1.1rem;font-size:0.9rem}
.nav a{color:var(--muted);text-decoration:none}
.nav a:hover{color:var(--ink)}
.hero h1{font-size:clamp(1.75rem,3.5vw,2.35rem);line-height:1.15;margin:0 0 0.6rem}
.hero p{margin:0 0 2rem;color:var(--muted);font-size:1.05rem;max-width:36rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.5rem}
.post{display:flex;flex-direction:column;background:var(--paper);border:1px solid var(--line);border-radius:4px;overflow:hidden;text-decoration:none;color:inherit;transition:border-color .15s}
.post:hover{border-color:#bbb}
.post img{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;background:#ddd}
.post-body{padding:1rem 1.1rem 1.2rem;display:flex;flex-direction:column;gap:0.45rem;flex:1}
.post-body h2{font-size:1.05rem;line-height:1.3;margin:0;font-weight:700}
.post-body p{margin:0;font-size:0.92rem;color:var(--muted);font-family:system-ui,sans-serif}
.article-wrap{max-width:720px;margin:0 auto}
.article-wrap .cover{width:100%;border-radius:4px;margin:0 0 1.5rem;aspect-ratio:16/9;object-fit:cover}
.article-wrap h1{font-size:clamp(1.5rem,3vw,2rem);line-height:1.2;margin:0 0 1rem}
.article-wrap h2,.article-wrap h3{margin-top:1.6em}
.article-wrap img{max-width:100%;height:auto;border-radius:4px}
.article-wrap figure{margin:1.5em 0}
.cta{margin-top:2.5rem;padding-top:1.25rem;border-top:1px solid var(--line);font-family:system-ui,sans-serif;font-size:0.9rem;color:var(--muted)}
.meta-line{font-family:system-ui,sans-serif;font-size:0.85rem;color:var(--muted);margin:0 0 1rem}
@media (max-width:560px){.grid{grid-template-columns:1fr}}
"""


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


def _site_chrome(inner: str, *, title: str, description: str, canonical: str, extra_head: str = "") -> str:
    zen = os.getenv("DZEN_ZEN_VERIFICATION", "").strip()
    yandex = os.getenv("DZEN_YANDEX_VERIFICATION", "").strip()
    metas = ""
    if zen:
        metas += f'<meta name="zen-verification" content="{html.escape(zen)}" />\n'
    if yandex:
        metas += f'<meta name="yandex-verification" content="{html.escape(yandex)}" />\n'
    metrika = _metrika_snippet()
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
<meta property="og:type" content="website">
<link rel="canonical" href="{html.escape(canonical)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="120x120" href="/favicon-120.png">
<link rel="apple-touch-icon" href="/favicon-120.png">
<link rel="alternate" type="application/rss+xml" title="МК Эксперт — RSS" href="/dzen-feed.xml">
{extra_head}<style>{BLOG_CSS}</style>
{metrika}</head>
<body>
<header class="site top">
<a class="brand" href="/">МК Эксперт</a>
<nav class="nav" aria-label="Меню">
<a href="/">Блог</a>
<a href="https://mkekspert.ru">Сайт</a>
<a href="https://mkekspert.ru/razbor-direct">Разбор Директа</a>
<a href="https://dzen.ru/klientyandtrafik">Дзен</a>
</nav>
</header>
{inner}
</body>
</html>
"""


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
    cover_block = (
        f'<img class="cover" src="{html.escape(cover_url)}" alt="{html.escape(title)}" width="1200" height="675">'
        if cover_url
        else ""
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "mainEntityOfPage": link,
        "author": {"@type": "Person", "name": "Мария Ковалева"},
        "publisher": {
            "@type": "Organization",
            "name": "МК Эксперт",
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL.rstrip('/')}/favicon-120.png"},
        },
        "inLanguage": "ru-RU",
    }
    if cover_url:
        schema["image"] = [cover_url]
    if post.get("published_at"):
        schema["datePublished"] = str(post["published_at"])[:10]
    og_image = f'<meta property="og:image" content="{html.escape(cover_url)}">\n' if cover_url else ""
    og_image += '<meta property="og:type" content="article">\n'
    extra = og_image + f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>\n'
    inner = f"""
<main class="site article-wrap">
{cover_block}
<p class="meta-line"><a href="/">← Все статьи</a> · Яндекс Директ · B2B</p>
<article>
{body}
</article>
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


def _blog_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _queue_items():
        post = _blog_post_meta(item)
        if not post or post["id"] in seen:
            continue
        seen.add(post["id"])
        posts.append(post)
    # published first, then approved
    posts.sort(key=lambda p: (0 if p["status"] == "published" else 1, p["title"]))
    return posts


def _blog_index_html() -> str:
    """Главная blog.mkekspert.ru — лента статей с обложками (SEO + Дзен)."""
    site = SITE_URL.rstrip("/")
    posts = _blog_posts()
    cards = []
    for p in posts:
        img = (
            f'<img src="{html.escape(p["cover_url"])}" alt="" loading="lazy" width="640" height="400">'
            if p["cover_url"]
            else ""
        )
        cards.append(
            f'<a class="post" href="/articles/{html.escape(p["id"])}.html">'
            f"{img}"
            f'<div class="post-body"><h2>{html.escape(p["title"])}</h2>'
            f'<p>{html.escape(p["description"][:180])}{"…" if len(p["description"]) > 180 else ""}</p>'
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
<h1>Блог о Яндекс Директе для B2B</h1>
<p>Кейсы с цифрами, разборы кабинета и практика. Без воды — только то, что работает в Директе.</p>
</section>
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


def _blog_sitemap_xml(posts: list[dict[str, Any]]) -> str:
    site = SITE_URL.rstrip("/")
    urls = [f"{site}/"] + [p["url"] for p in posts]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        lines.append(f"  <url><loc>{html.escape(u)}</loc></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _collect_gh_pages_files() -> dict[str, bytes]:
    """Файлы для ветки gh-pages: блог, feed, covers, SEO."""
    files: dict[str, bytes] = {}
    if FEED_FILE.is_file():
        files["dzen-feed.xml"] = FEED_FILE.read_bytes()
    files["CNAME"] = b"blog.mkekspert.ru\n"
    files["robots.txt"] = (
        "User-agent: *\nAllow: /\nSitemap: https://blog.mkekspert.ru/sitemap.xml\n"
    ).encode()
    posts = _blog_posts()
    files["index.html"] = _blog_index_html().encode("utf-8")
    files["sitemap.xml"] = _blog_sitemap_xml(posts).encode("utf-8")
    if BLOG_SITE_DIR.is_dir():
        for path in BLOG_SITE_DIR.rglob("*"):
            if not path.is_file() or path.name.startswith("."):
                continue
            rel = path.relative_to(BLOG_SITE_DIR).as_posix()
            if rel == "index.html":
                continue
            files[rel] = path.read_bytes()
    if COVERS_DIR.is_dir():
        for cover in COVERS_DIR.glob("*.jpg"):
            files[f"covers/{cover.name}"] = cover.read_bytes()
    for item in _queue_items():
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


def deploy_gh_pages(*, campaign_id: str = "", dry_run: bool = False) -> str:
    """Деплой на GitHub Pages (ветка gh-pages) → blog.mkekspert.ru."""
    if os.getenv("DZEN_RSS_DEPLOY_GH_PAGES", "true").lower() not in ("1", "true", "yes"):
        return ""
    files = _collect_gh_pages_files()
    if not files:
        return "gh-pages: нет файлов для деплоя"

    git_root = _git_root()
    worktree = git_root / ".gh-pages-deploy"
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

    if worktree.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=git_root,
            capture_output=True,
        )

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

    for entry in worktree.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()

    for rel_path, content in files.items():
        dest = worktree / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

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
        # ветка только для деплоя сайта — перезаписываем содержимое
        push = subprocess.run(
            ["git", "push", "--force-with-lease", "origin", "HEAD:gh-pages"],
            cwd=worktree,
            capture_output=True,
            text=True,
        )
        if push.returncode != 0:
            print(f"⚠ gh-pages push: {(push.stderr or push.stdout).strip()}")
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=git_root,
                capture_output=True,
            )
            return ""
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
            link_path = ARCHIVE_SITE_LINKS[len(blocks) % len(ARCHIVE_SITE_LINKS)]
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
