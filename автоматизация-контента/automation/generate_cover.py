#!/usr/bin/env python3
"""Обложки для Дзен / TG / VK — GPT (OpenAI) + текстовый оверлей в стиле mkekspert."""

from __future__ import annotations

import argparse
import base64
import os
import re
import textwrap
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "assets" / "covers"
IMPORT_DIR = COVERS / "_import"
ENV_FILE = Path(__file__).resolve().parent / ".env"
QUEUE_FILE = ROOT / "queue" / "publish-queue.yaml"
POSTS_QUEUE_FILE = ROOT / "queue" / "posts-queue.yaml"
BRAND_VISUAL = ROOT / "references" / "brand-visual.md"

# Палитра mkekspert.ru + VK
BG = "#181818"
ACCENT_GREEN = "#4EAF4E"
ACCENT_YELLOW = "#FFCC4A"
TEXT = "#FFFFFF"
SUB = "#B0B0B0"

LANDSCAPE = (1200, 630)
VK_PORTRAIT = (1080, 1350)  # 4:5 — без обрезки в квадрат
SQUARE = (1080, 1080)  # legacy, не использовать для VK-ленты


def load_env() -> None:
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
    load_dotenv()


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def gpt_prompt(headline: str, subline: str, *, vk: bool = False, square: bool = False) -> str:
    if vk:
        ratio = "4:5 vertical portrait"
    elif square:
        ratio = "1:1 square"
    else:
        ratio = "16:9 landscape"
    return (
        f"Bright bold social media cover, {ratio}, dark charcoal background {BG}, "
        f"vibrant green {ACCENT_GREEN} and golden yellow {ACCENT_YELLOW} accents, "
        "modern B2B digital marketing style, high contrast, eye-catching in mobile feed. "
        f'Large prominent typography area for headline "{headline}" and metric "{subline}". '
        "Abstract growth chart, upward arrow, context advertising dashboard elements, "
        "no human faces, no stock photo people, no watermark, clean professional Russian business aesthetic."
    )


def generate_gpt_image(prompt: str, size: str = "1536x1024") -> Image.Image:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан в .env")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("pip install openai") from exc

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    resp = client.images.generate(model=model, prompt=prompt, size=size, quality="high", n=1)
    b64 = resp.data[0].b64_json
    if not b64:
        raise RuntimeError("OpenAI не вернул изображение")
    import io

    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def generate_gpt_dalle_fallback(prompt: str, size: str = "1792x1024") -> Image.Image:
    """DALL·E 3 если gpt-image-1 недоступен."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.images.generate(model="dall-e-3", prompt=prompt, size=size, quality="hd", n=1)
    url = resp.data[0].url
    if not url:
        raise RuntimeError("DALL·E не вернул URL")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    import io

    return Image.open(io.BytesIO(r.content)).convert("RGB")


def fetch_gpt_background(headline: str, subline: str, *, vk: bool = False, square: bool = False) -> Image.Image:
    prompt = gpt_prompt(headline, subline, vk=vk, square=square)
    if vk:
        size, dalle = "1024x1536", "1024x1792"
    elif square:
        size, dalle = "1024x1024", "1024x1024"
    else:
        size, dalle = "1536x1024", "1792x1024"
    try:
        return generate_gpt_image(prompt, size=size)
    except Exception:
        return generate_gpt_dalle_fallback(prompt, size=dalle)


def overlay_brand_text(img: Image.Image, headline: str, subline: str) -> Image.Image:
    """Полупрозрачная подложка + текст для читаемости."""
    img = img.copy()
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, int(h * 0.55), w, h], fill=(24, 24, 24, 210))
    draw.rectangle([0, 0, 14, h], fill=ACCENT_GREEN)
    draw.rectangle([0, h - 8, w, h], fill=ACCENT_YELLOW)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_h = load_font(max(36, w // 22), bold=True)
    font_s = load_font(max(22, w // 32))
    font_b = load_font(max(18, w // 38))

    y = int(h * 0.58)
    for line in textwrap.wrap(headline, width=22)[:3]:
        draw.text((max(50, w // 20), y), line, fill=TEXT, font=font_h)
        y += int(h * 0.09)

    if subline:
        y += 8
        for line in textwrap.wrap(subline, width=36)[:2]:
            draw.text((max(50, w // 20), y), line, fill=ACCENT_YELLOW, font=font_s)
            y += int(h * 0.06)

    draw.text((max(50, w // 20), h - 45), "Мария Ковалева · mkekspert.ru", fill=ACCENT_GREEN, font=font_b)
    return img


def hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def crop_center_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def resize_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def find_import_background(slug: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = IMPORT_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    return None


def draw_bright_background(size: tuple[int, int]) -> Image.Image:
    """Яркий бренд-фон без GPT: градиент + абстрактные акценты."""
    w, h = size
    img = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(img)

    bg0, bg1 = hex_rgb("#151515"), hex_rgb(BG)
    green = hex_rgb(ACCENT_GREEN)
    yellow = hex_rgb(ACCENT_YELLOW)

    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(bg0[i] * (1 - t) + bg1[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)

    # светящиеся пятна
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.ellipse([int(w * 0.58), int(-h * 0.1), int(w * 1.1), int(h * 0.5)], fill=(*green, 55))
    odraw.ellipse([int(-w * 0.2), int(h * 0.35), int(w * 0.45), int(h * 1.05)], fill=(*yellow, 45))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # абстрактный рост (столбики)
    base_y = int(h * 0.72)
    bars = [0.22, 0.34, 0.48, 0.62, 0.78]
    bar_w = max(18, w // 28)
    gap = max(10, w // 48)
    x = int(w * 0.62)
    for i, bh in enumerate(bars):
        top = base_y - int(h * bh * 0.35)
        color = green if i >= 3 else (80, 80, 80)
        draw.rounded_rectangle([x, top, x + bar_w, base_y], radius=6, fill=color)
        x += bar_w + gap

    # стрелка вверх
    ax, ay = int(w * 0.78), int(h * 0.28)
    draw.polygon(
        [(ax, ay - 70), (ax + 55, ay + 10), (ax + 18, ay + 10), (ax + 18, ay + 90), (ax - 18, ay + 90), (ax - 18, ay + 10), (ax - 55, ay + 10)],
        fill=yellow,
    )

    draw.rectangle([0, 0, 14, h], fill=ACCENT_GREEN)
    draw.rectangle([0, h - 8, w, h], fill=ACCENT_YELLOW)
    return img


def _format_num(s: str) -> str:
    digits = re.sub(r"\D", "", s)
    if not digits:
        return s.strip()
    return f"{int(digits):,}".replace(",", " ")


def _parse_cover_copy(headline: str, subline: str, *, stats: list[str] | None = None) -> dict[str, str | list[str]]:
    h = headline.replace("–", "→").replace("->", "→")
    m = re.search(r"(\d[\d\s]*)\s*→\s*(\d[\d\s]*)", h)
    tag = "КЕЙС B2B"
    niche = ""
    if subline:
        parts = [p.strip() for p in re.split(r"[·•]", subline) if p.strip()]
        for p in parts:
            if re.search(r"b2b|кейс", p, re.I):
                tag = p.upper() if len(p) < 20 else "КЕЙС B2B"
            else:
                niche = p
    metric_label = "CPL заявки"
    if re.search(r"cpl", h, re.I):
        metric_label = "CPL заявки"
    elif re.search(r"заяв", h, re.I):
        metric_label = "заявки"
    hook = niche or subline or "Яндекс Директ"
    extra_stats = [s.strip() for s in (stats or []) if s and s.strip()]
    if m:
        was_raw = int(re.sub(r"\D", "", m.group(1)) or "0")
        now_raw = int(re.sub(r"\D", "", m.group(2)) or "0")
        multiplier = ""
        if was_raw > 0 and now_raw > 0 and was_raw > now_raw:
            ratio = was_raw / now_raw
            multiplier = f"×{ratio:.0f}" if ratio >= 1.5 else ""
        return {
            "mode": "metric",
            "tag": tag,
            "was": _format_num(m.group(1)),
            "now": _format_num(m.group(2)),
            "metric_label": metric_label,
            "niche": niche,
            "hook": f"{niche} · Директ" if niche else "Разбор рекламы",
            "multiplier": multiplier,
            "stats": extra_stats,
        }
    return {
        "mode": "text",
        "tag": tag,
        "title": headline.rstrip(".?!"),
        "subtitle": subline,
        "hook": hook,
        "stats": extra_stats,
    }


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> float:
    return draw.textlength(text, font=font)


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str | tuple[int, int, int],
    canvas_w: int,
) -> None:
    x = int((canvas_w - _text_width(draw, text, font)) // 2)
    draw.text((x, y), text, fill=fill, font=font)


def _draw_strikethrough(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str | tuple[int, int, int],
) -> None:
    draw.text((x, y), text, fill=fill, font=font)
    tw = _text_width(draw, text, font)
    mid_y = y + font.size // 2
    draw.line([(x, mid_y), (x + int(tw), mid_y)], fill=fill, width=max(3, font.size // 18))


def _draw_stat_chip(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    value: str,
    label: str,
    *,
    accent: str = ACCENT_GREEN,
    value_fill: str = TEXT,
) -> None:
    draw.rounded_rectangle([x, y, x + w, y + h], radius=22, fill="#1a1a1a", outline=accent, width=2)
    font_v = load_font(34, bold=True)
    font_l = load_font(24)
    draw.text((x + 24, y + 18), value, fill=value_fill, font=font_v)
    draw.text((x + 24, y + 58), label, fill="#9a9a9a", font=font_l)


def draw_vk_smm_cover(headline: str, subline: str, *, stats: list[str] | None = None) -> Image.Image:
    """Вертикальная обложка 4:5 под ленту VK — нативный SMM-макет."""
    w, h = VK_PORTRAIT
    green = hex_rgb(ACCENT_GREEN)
    yellow = hex_rgb(ACCENT_YELLOW)
    meta = _parse_cover_copy(headline, subline, stats=stats)

    img = Image.new("RGB", (w, h), "#0c0c0c")
    draw = ImageDraw.Draw(img)

    # градиент + мягкое свечение
    for y in range(h):
        t = y / max(h - 1, 1)
        base = int(10 + 18 * t)
        draw.line([(0, y), (w, y)], fill=(base, base, base + 3))

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([w - 640, -240, w + 120, 520], fill=(*green, 70))
    gd.ellipse([-280, int(h * 0.42), 420, h + 200], fill=(*yellow, 50))
    gd.ellipse([int(w * 0.15), int(h * 0.55), int(w * 0.95), int(h * 0.98)], fill=(40, 40, 40, 90))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    # бренд-полосы
    draw.rectangle([0, 0, 14, h], fill=ACCENT_GREEN)
    draw.rectangle([0, h - 8, w, h], fill=ACCENT_YELLOW)

    pad = 52

    # тег + ниша
    font_tag = load_font(28, bold=True)
    tag = str(meta.get("tag", "КЕЙС"))
    tag_w = int(_text_width(draw, tag, font_tag)) + 44
    draw.rounded_rectangle([pad, 44, pad + tag_w, 98], radius=24, fill=green)
    draw.text((pad + 22, 54), tag, fill="#0a1a0a", font=font_tag)

    if meta["mode"] == "metric":
        niche = str(meta.get("niche") or "Яндекс Директ")
        font_niche = load_font(34, bold=True)
        niche_cap = niche[0].upper() + niche[1:] if niche else ""
        draw.text((pad + tag_w + 20, 56), niche_cap, fill="#d8d8d8", font=font_niche)

        # мини-график справа вверху
        chart_x, chart_y = w - pad - 180, 70
        bars = [28, 42, 56, 78, 96]
        bar_w = 22
        for i, bh in enumerate(bars):
            color = green if i >= 3 else (55, 55, 55)
            bx = chart_x + i * (bar_w + 10)
            draw.rounded_rectangle([bx, chart_y + 100 - bh, bx + bar_w, chart_y + 100], radius=5, fill=color)

        # блок «было» — компактно, по центру
        font_was = load_font(52, bold=True)
        font_was_lbl = load_font(26)
        was_text = f"{meta['was']} ₽"
        was_y = 200
        was_x = int((w - _text_width(draw, was_text, font_was)) // 2)
        _draw_strikethrough(draw, was_text, was_x, was_y, font_was, "#c07070")
        _draw_text_centered(draw, "было", was_y - 34, font_was_lbl, "#666666", w)

        # стрелка вниз = снижение стоимости (хорошо)
        ax = w // 2
        draw.rounded_rectangle([ax - 34, 290, ax + 34, 360], radius=18, fill="#1f1f1f", outline=green, width=2)
        draw.polygon([(ax, 338), (ax + 16, 312), (ax - 16, 312)], fill=green)

        # герой — результат
        font_now = load_font(128, bold=True)
        font_metric = load_font(38, bold=True)
        now_text = f"{meta['now']} ₽"
        now_y = 400
        _draw_text_centered(draw, now_text, now_y, font_now, TEXT, w)
        _draw_text_centered(draw, str(meta["metric_label"]), now_y + 138, font_metric, ACCENT_YELLOW, w)

        # бейдж ×3
        multiplier = str(meta.get("multiplier") or "")
        chip_y = 580
        if multiplier:
            badge = f"{multiplier} дешевле"
            font_badge = load_font(36, bold=True)
            badge_w = int(_text_width(draw, badge, font_badge)) + 56
            badge_x = (w - badge_w) // 2
            draw.rounded_rectangle([badge_x, chip_y, badge_x + badge_w, chip_y + 64], radius=32, fill=yellow)
            draw.text((badge_x + 28, chip_y + 12), badge, fill="#1a1400", font=font_badge)
            chip_y += 88

        # доп. метрики кейса
        stat_lines = list(meta.get("stats") or [])
        if not stat_lines:
            stat_lines = ["59 заявок/мес", "0,1% → 3%"]
        chip_h = 96
        gap = 20
        if len(stat_lines) >= 2:
            chip_w = (w - pad * 2 - gap) // 2
            _draw_stat_chip(draw, pad, chip_y, chip_w, chip_h, stat_lines[0], "после перезапуска")
            _draw_stat_chip(
                draw, pad + chip_w + gap, chip_y, chip_w, chip_h,
                stat_lines[1], "конверсия сайта", accent=ACCENT_YELLOW, value_fill=ACCENT_YELLOW,
            )
        elif stat_lines:
            chip_w = w - pad * 2
            _draw_stat_chip(draw, pad, chip_y, chip_w, chip_h, stat_lines[0], "результат")

        # подпись канала
        draw.text((pad, h - 96), "Мария Ковалева · Яндекс Директ", fill=ACCENT_GREEN, font=load_font(30, bold=True))
        draw.text((pad, h - 58), "mkekspert.ru · кейс на Дзен", fill="#707070", font=load_font(26))
    else:
        font_title = load_font(68, bold=True)
        font_sub = load_font(38, bold=True)
        y = 200
        for line in textwrap.wrap(str(meta["title"]), width=14)[:3]:
            _draw_text_centered(draw, line, y, font_title, TEXT, w)
            y += 82
        if meta.get("subtitle"):
            for line in textwrap.wrap(str(meta["subtitle"]), width=22)[:2]:
                _draw_text_centered(draw, line, y + 16, font_sub, ACCENT_YELLOW, w)
                y += 50
        draw.text((pad, h - 88), "Мария Ковалева · Яндекс Директ", fill=ACCENT_GREEN, font=load_font(30, bold=True))
        draw.text((pad, h - 52), "mkekspert.ru", fill="#666666", font=load_font(26))

    return img


def generate_pil_fallback(headline: str, subline: str, size: tuple[int, int]) -> Image.Image:
    if size == VK_PORTRAIT:
        return draw_vk_smm_cover(headline, subline)
    img = draw_bright_background(size)
    return overlay_brand_text(img, headline, subline)


def resize_contain(img: Image.Image, size: tuple[int, int], *, bg: str = BG) -> Image.Image:
    """Вписать целиком без обрезки (для VK из горизонтальной обложки)."""
    tw, th = size
    iw, ih = img.size
    scale = min(tw / iw, th / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, bg)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def landscape_to_vk_cover(landscape: Image.Image) -> Image.Image:
    return resize_contain(landscape, VK_PORTRAIT)


def load_background_image(path: Path, *, vk: bool = False, square: bool = False, target: tuple[int, int]) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if vk:
        return resize_contain(img, target)
    if square:
        img = crop_center_square(img)
    return resize_cover(img, target)


def generate_cover(
    headline: str,
    subline: str,
    out: Path,
    *,
    vk: bool = False,
    square: bool = False,
    use_gpt: bool = True,
    slug: str = "",
    import_path: Path | None = None,
    from_landscape: Path | None = None,
    vk_stats: list[str] | None = None,
) -> Path:
    if vk:
        target = VK_PORTRAIT
    elif square:
        target = SQUARE
    else:
        target = LANDSCAPE
    img: Image.Image | None = None

    if from_landscape and from_landscape.exists():
        img = landscape_to_vk_cover(Image.open(from_landscape).convert("RGB"))
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, "JPEG", quality=92)
        return out

    bg_path = import_path or (find_import_background(slug) if slug else None)
    if bg_path:
        try:
            bg = load_background_image(bg_path, vk=vk, square=square, target=target)
            img = overlay_brand_text(bg, headline, subline)
        except Exception as exc:
            print(f"⚠ import {bg_path.name}: {exc}")

    if img is None and use_gpt and os.getenv("OPENAI_API_KEY"):
        try:
            bg = fetch_gpt_background(headline, subline, vk=vk, square=square)
            bg = bg.resize(target, Image.Resampling.LANCZOS)
            img = overlay_brand_text(bg, headline, subline)
        except Exception as exc:
            print(f"⚠ GPT: {exc} — fallback PIL")

    if img is None:
        if vk:
            img = draw_vk_smm_cover(headline, subline, stats=vk_stats)
        else:
            img = generate_pil_fallback(headline, subline, target)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out


def cover_paths(slug: str) -> tuple[Path, Path]:
    return COVERS / f"{slug}.jpg", COVERS / f"{slug}-vk.jpg"


def ensure_covers(slug: str, headline: str, subline: str = "", *, force: bool = False, vk_stats: list[str] | None = None) -> tuple[Path, Path]:
    landscape, vk_cover = cover_paths(slug)
    if force or not landscape.exists():
        generate_cover(headline, subline, landscape, square=False, slug=slug)
        print(f"✓ {landscape}")
    if force or not vk_cover.exists():
        generate_cover(headline, subline, vk_cover, vk=True, slug=slug, use_gpt=False, vk_stats=vk_stats)
        print(f"✓ {vk_cover}")
    elif force:
        generate_cover(headline, subline, vk_cover, vk=True, slug=slug, use_gpt=False, vk_stats=vk_stats)
        print(f"✓ {vk_cover}")
    return landscape, vk_cover


def resolve_cover_for_item(item: dict, *, vk: bool = False) -> Path | None:
    rel = item.get("cover", "")
    if not rel:
        return None
    base = ROOT / rel
    if vk:
        vk_path = base.with_name(base.stem + "-vk" + base.suffix)
        if vk_path.exists():
            return vk_path
    return base if base.exists() else None


def _headline_from_post(path: Path) -> tuple[str, str]:
    headline = ""
    subline = ""
    if path.exists():
        raw = path.read_text(encoding="utf-8")
        if raw.startswith("---"):
            meta = yaml.safe_load(raw.split("---", 2)[1]) or {}
            headline = str(meta.get("cover_headline") or meta.get("title", ""))[:80]
            subline = str(meta.get("cover_subline") or "")[:60]
        if not headline:
            for line in raw.splitlines():
                s = line.strip().strip("*").strip()
                if s and not s.startswith("#") and not s.startswith("http"):
                    headline = s[:80]
                    break
    return headline, subline


def ensure_cover_for_queue_id(campaign_id: str, *, force: bool = False) -> Path | None:
    if not QUEUE_FILE.exists():
        return None
    data = yaml.safe_load(QUEUE_FILE.read_text(encoding="utf-8")) or {}
    item = next((i for i in data.get("items", []) if i.get("id") == campaign_id), None)
    if not item:
        return None

    slug = Path(item.get("cover", f"assets/covers/{campaign_id}.jpg")).stem.replace("-vk", "")
    headline = item.get("cover_headline", "")
    subline = item.get("cover_subline", "")
    vk_stats = item.get("cover_vk_stats") or None

    if not headline:
        article = item.get("dzen_article", "")
        if article:
            headline, subline = _headline_from_post(ROOT / article)
    if not headline:
        headline = campaign_id.replace("-", " ").title()

    landscape, _ = ensure_covers(slug, headline, subline, force=force, vk_stats=vk_stats)
    item["cover"] = f"assets/covers/{slug}.jpg"
    items = data.get("items", [])
    for i, it in enumerate(items):
        if it.get("id") == campaign_id:
            items[i] = item
            break
    QUEUE_FILE.write_text(
        yaml.dump({"items": items}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return landscape


def ensure_cover_for_post(post_id: str, post_path: Path, *, force: bool = False) -> Path | None:
    headline = ""
    subline = ""
    if POSTS_QUEUE_FILE.exists():
        data = yaml.safe_load(POSTS_QUEUE_FILE.read_text(encoding="utf-8")) or {}
        item = next((i for i in data.get("items", []) if i.get("id") == post_id), None)
        if item:
            headline = str(item.get("cover_headline", ""))[:80]
            subline = str(item.get("cover_subline", ""))[:60]
    if not headline:
        headline, subline = _headline_from_post(post_path)
    if not headline:
        headline = post_id.replace("-", " ").replace("tg ", "").replace("vk ", "").title()
    landscape, _ = ensure_covers(post_id, headline, subline, force=force)
    return landscape


def main() -> None:
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--title", required=True, help="Крупный текст на обложке")
    p.add_argument("--subtitle", default="")
    p.add_argument("--variant", choices=["landscape", "vk", "both"], default="both")
    p.add_argument("--no-gpt", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--campaign", help="id из publish-queue.yaml")
    p.add_argument("--import", dest="import_file", help="PNG/JPG фон (или положите в assets/covers/_import/{slug}.png)")
    args = p.parse_args()

    if args.campaign:
        path = ensure_cover_for_queue_id(args.campaign, force=args.force)
        if path:
            print(path)
        return

    use_gpt = not args.no_gpt
    import_path = Path(args.import_file) if args.import_file else None
    if args.variant in ("landscape", "both"):
        out = COVERS / f"{args.slug}.jpg"
        if args.force or not out.exists():
            generate_cover(
                args.title, args.subtitle, out,
                square=False, use_gpt=use_gpt, slug=args.slug, import_path=import_path,
            )
            print(out)
    if args.variant in ("vk", "both"):
        out = COVERS / f"{args.slug}-vk.jpg"
        if args.force or not out.exists():
            generate_cover(
                args.title, args.subtitle, out,
                vk=True, use_gpt=use_gpt, slug=args.slug, import_path=import_path,
            )
            print(out)


if __name__ == "__main__":
    main()
