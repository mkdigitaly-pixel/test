#!/usr/bin/env python3
"""Генерация обложки 1200×630 для статей Дзена (бренд mkekspert)."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
COVERS = ROOT / "assets" / "covers"

BG = "#181818"
ACCENT = "#4eaf4e"
TEXT = "#ffffff"
SUB = "#b0b0b0"
W, H = 1200, 630


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_title(title: str, width: int = 28) -> list[str]:
    title = title.rstrip(".")
    lines = textwrap.wrap(title, width=width)
    return lines[:4]  # не больше 4 строк


def generate(title: str, subtitle: str, out: Path) -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # зелёная полоса слева
    draw.rectangle([0, 0, 12, H], fill=ACCENT)
    draw.rectangle([0, H - 6, W, H], fill=ACCENT)

    font_title = load_font(46, bold=True)
    font_sub = load_font(26)
    font_brand = load_font(22)

    y = 120
    for line in wrap_title(title):
        draw.text((80, y), line, fill=TEXT, font=font_title)
        y += 58

    if subtitle:
        y += 20
        for line in textwrap.wrap(subtitle, width=42)[:2]:
            draw.text((80, y), line, fill=SUB, font=font_sub)
            y += 36

    draw.text((80, H - 70), "Мария Ковалева · Яндекс Директ", fill=ACCENT, font=font_brand)
    draw.text((80, H - 38), "mkekspert.ru", fill=SUB, font=font_brand)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=92)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="Разбор с практики, без воды")
    p.add_argument("--slug", required=True, help="имя файла без расширения")
    args = p.parse_args()
    out = COVERS / f"{args.slug}.jpg"
    path = generate(args.title, args.subtitle, out)
    print(path)


if __name__ == "__main__":
    main()
