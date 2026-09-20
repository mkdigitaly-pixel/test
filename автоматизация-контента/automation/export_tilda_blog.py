#!/usr/bin/env python3
"""
Экспорт красивого блока блога для Tilda (HTML / T123 / Zero Block).

  python3 export_tilda_blog.py
  python3 export_tilda_blog.py --limit 6

Пишет:
  content/tilda-blog-block.html  — вставить в Tilda → Блок HTML
  content/tilda-blog-page.md     — инструкция страницы /blog или секции
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dzen_rss import _blog_posts  # noqa: E402


OUT_HTML = ROOT / "content" / "tilda-blog-block.html"
OUT_MD = ROOT / "content" / "tilda-blog-page.md"


def build_block(limit: int = 6) -> str:
    posts = _blog_posts()[:limit]
    cards = []
    for p in posts:
        cover = html.escape(p.get("cover_url") or "")
        title = html.escape(p.get("title") or "")
        desc = html.escape((p.get("description") or "")[:140])
        if len(p.get("description") or "") > 140:
            desc += "…"
        url = html.escape(p.get("url") or f"https://blog.mkekspert.ru/articles/{p['id']}.html")
        kicker = html.escape(p.get("keyword") or "Директ")
        img = (
            f'<div class="mkb-media"><img src="{cover}" alt="" loading="lazy"></div>'
            if cover
            else '<div class="mkb-media mkb-media--empty"></div>'
        )
        cards.append(
            f"""<a class="mkb-card" href="{url}" target="_blank" rel="noopener">
  {img}
  <div class="mkb-body">
    <div class="mkb-kicker">{kicker}</div>
    <div class="mkb-title">{title}</div>
    <div class="mkb-desc">{desc}</div>
    <div class="mkb-more">Читать на блоге →</div>
  </div>
</a>"""
        )
    grid = "\n".join(cards)
    return f"""<!-- mkekspert blog block for Tilda HTML (T123). Палитра = обложки / brandbook. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Unbounded:wght@500;600&display=swap" rel="stylesheet">
<style>
.mkb-wrap{{
  --bg:#f3ebe3;--panel:#fffcf8;--line:#e6d9cc;--ink:#3d3d3d;--muted:#8b6b4a;
  --terra:#a85a32;--green:#2a6f4c;--gold:#d4af37;--sand:#d4a373;--blush:#f5d6c6;
  font-family:"Manrope",Arial,sans-serif;color:var(--ink);
  background:
    radial-gradient(900px 380px at 8% 0%,rgba(245,214,198,.75),transparent 55%),
    radial-gradient(700px 320px at 92% 10%,rgba(212,175,55,.16),transparent 50%),
    var(--bg);
  padding:48px 20px 56px;border-radius:0;
}}
.mkb-inner{{max-width:1100px;margin:0 auto}}
.mkb-brand{{
  font-family:"Unbounded",Arial,sans-serif;font-size:14px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--terra);margin:0 0 12px;font-weight:700;
}}
.mkb-h{{
  font-family:"Unbounded",Arial,sans-serif;font-size:clamp(28px,4vw,42px);
  line-height:1.15;margin:0 0 12px;letter-spacing:-.03em;font-weight:600;max-width:16ch;
  color:var(--ink);
}}
.mkb-lead{{margin:0 0 28px;color:var(--muted);font-size:17px;max-width:42ch;line-height:1.5}}
.mkb-cta{{
  display:inline-block;margin:0 0 36px;padding:14px 22px;background:var(--terra);
  color:#fff!important;text-decoration:none;font-weight:700;border-radius:999px;
  box-shadow:0 10px 28px rgba(168,90,50,.22);
}}
.mkb-cta:hover{{background:var(--green)}}
.mkb-label{{
  font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
  margin:0 0 16px;display:flex;align-items:center;gap:12px;
}}
.mkb-label:after{{content:"";flex:1;height:1px;background:var(--line)}}
.mkb-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.mkb-card{{
  display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);
  border-radius:18px;overflow:hidden;text-decoration:none;color:inherit;
  box-shadow:0 8px 28px rgba(61,45,30,.06);
  transition:transform .2s,border-color .2s,box-shadow .2s;
}}
.mkb-card:hover{{transform:translateY(-4px);border-color:rgba(168,90,50,.35);box-shadow:0 18px 40px rgba(61,45,30,.12)}}
.mkb-media{{background:#efe4d8;overflow:hidden;position:relative;aspect-ratio:16/9}}
.mkb-media:after{{
  content:"";position:absolute;left:0;right:0;bottom:0;height:3px;z-index:1;
  background:linear-gradient(90deg,var(--terra),var(--gold),var(--green));
}}
.mkb-media img{{width:100%;height:100%;object-fit:contain;object-position:center;display:block}}
.mkb-media--empty{{aspect-ratio:16/9;background:linear-gradient(135deg,#efe4d8,#f5d6c6)}}
.mkb-body{{padding:16px 16px 18px;display:flex;flex-direction:column;gap:8px;flex:1}}
.mkb-kicker{{
  font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--green);font-weight:700;
  display:inline-flex;align-self:flex-start;padding:4px 10px;border-radius:999px;background:rgba(42,111,76,.1);
}}
.mkb-title{{font-family:"Unbounded",Arial,sans-serif;font-size:15px;line-height:1.35;font-weight:500;letter-spacing:-.02em;color:var(--ink)}}
.mkb-desc{{font-size:14px;color:var(--muted);line-height:1.45}}
.mkb-more{{margin-top:auto;padding-top:8px;font-size:13px;color:var(--terra);font-weight:700}}
.mkb-all{{
  display:inline-block;margin-top:28px;color:var(--terra)!important;font-weight:700;text-decoration:none;
}}
@media (max-width:900px){{.mkb-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media (max-width:560px){{.mkb-grid{{grid-template-columns:1fr}}.mkb-wrap{{padding:36px 16px 44px}}}}
</style>
<div class="mkb-wrap">
  <div class="mkb-inner">
    <div class="mkb-brand">МК Эксперт</div>
    <h2 class="mkb-h">Блог о Директе для B2B</h2>
    <p class="mkb-lead">Кейсы с цифрами и разборы кабинета — без воды, только практика.</p>
    <a class="mkb-cta" href="https://mkekspert.ru/razbor-direct?utm_source=site&utm_medium=blog-block&utm_campaign=tilda">Бесплатный разбор</a>
    <div class="mkb-label">Свежие статьи</div>
    <div class="mkb-grid">
{grid}
    </div>
    <a class="mkb-all" href="https://blog.mkekspert.ru/?utm_source=site&utm_medium=blog-block&utm_campaign=tilda">Все статьи на blog.mkekspert.ru →</a>
  </div>
</div>
"""


def build_instructions() -> str:
    return """# Tilda — страница / секция «Блог»

Готовый HTML: [`tilda-blog-block.html`](tilda-blog-block.html)  
Стиль = палитра сайта: `#121212` / `#4EAF4E` / `#FFCC4A`.

## Куда вставить

### Вариант A — секция на главной
1. Tilda → страница главная → **добавить блок** → **HTML** (T123) или Zero Block → HTML
2. Вставить содержимое `tilda-blog-block.html`
3. Опубликовать сайт

### Вариант B — отдельная страница `/blog`
1. Создать страницу с адресом `blog`
2. Title: `Блог о Яндекс Директе — МК Эксперт`
3. Description: `Кейсы и разборы Директа для B2B. CPL, заявки, Метрика.`
4. Вставить тот же HTML-блок
5. В меню добавить пункт **Блог** → `/blog`
6. Опционально: редирект `/blog` уже не 404

## Обновление карточек

После новых статей:

```bash
cd автоматизация-контента/automation
python3 export_tilda_blog.py
```

Скопировать свежий HTML в Tilda снова (Tilda не подтягивает с blog автоматически).

Полные тексты статей остаются на **blog.mkekspert.ru** (SEO + RSS Дзен).  
На Tilda — витрина с обложками и ссылками.

## Чеклист
- [ ] HTML вставлен и выглядит на мобилке
- [ ] Кнопка «Бесплатный разбор» ведёт на `/razbor-direct`
- [ ] «Все статьи» → blog.mkekspert.ru
- [ ] Пункт меню «Блог»
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    OUT_HTML.write_text(build_block(args.limit), encoding="utf-8")
    OUT_MD.write_text(build_instructions(), encoding="utf-8")
    print(f"OK → {OUT_HTML.relative_to(ROOT)}")
    print(f"OK → {OUT_MD.relative_to(ROOT)}")
    print(f"Карточек: {min(args.limit, len(_blog_posts()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
