#!/usr/bin/env python3
"""Обложки для Дзен / TG / VK — GPT (OpenAI) + текстовый оверлей в стиле mkekspert."""

from __future__ import annotations

import argparse
import base64
import os
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


def generate_pil_fallback(headline: str, subline: str, size: tuple[int, int]) -> Image.Image:
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
        img = generate_pil_fallback(headline, subline, target)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out


def cover_paths(slug: str) -> tuple[Path, Path]:
    return COVERS / f"{slug}.jpg", COVERS / f"{slug}-vk.jpg"


def ensure_covers(slug: str, headline: str, subline: str = "", *, force: bool = False) -> tuple[Path, Path]:
    landscape, vk_cover = cover_paths(slug)
    if force or not landscape.exists():
        generate_cover(headline, subline, landscape, square=False, slug=slug)
        print(f"✓ {landscape}")
    if force or not vk_cover.exists():
        if landscape.exists():
            generate_cover(headline, subline, vk_cover, from_landscape=landscape)
        else:
            generate_cover(headline, subline, vk_cover, vk=True, slug=slug)
        print(f"✓ {vk_cover}")
    elif force and landscape.exists():
        generate_cover(headline, subline, vk_cover, from_landscape=landscape)
        print(f"✓ {vk_cover} (из landscape)")
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

    if not headline:
        article = item.get("dzen_article", "")
        if article:
            headline, subline = _headline_from_post(ROOT / article)
    if not headline:
        headline = campaign_id.replace("-", " ").title()

    landscape, _ = ensure_covers(slug, headline, subline, force=force)
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
        landscape = COVERS / f"{args.slug}.jpg"
        if args.force or not out.exists():
            if landscape.exists():
                generate_cover(args.title, args.subtitle, out, from_landscape=landscape)
            else:
                generate_cover(
                    args.title, args.subtitle, out,
                    vk=True, use_gpt=use_gpt, slug=args.slug, import_path=import_path,
                )
            print(out)


if __name__ == "__main__":
    main()
