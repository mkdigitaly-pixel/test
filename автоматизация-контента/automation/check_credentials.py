#!/usr/bin/env python3
"""Проверка .env без печати секретов: python3 check_credentials.py"""
from pathlib import Path
import os
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(root / "ДОСТУПЫ.env", override=True)

GROUPS = [
    ("Tilda", ["TILDA_PUBLIC_KEY", "TILDA_SECRET_KEY", "TILDA_PROJECT_ID", "TILDA_PAGE_RAZBOR_ID"]),
    ("Telegram", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_MAIN_CHANNEL_ID", "TELEGRAM_DZEN_CHANNEL_ID"]),
    ("VK", ["VK_ACCESS_TOKEN", "VK_GROUP_ID", "VK_USER_TOKEN"]),
    ("SEO SERP", ["SEO_SERP_PROVIDER", "SEO_SERP_USER", "SEO_SERP_KEY"]),
    ("OpenRouter", ["OPENROUTER_API_KEY"]),
    ("Yandex optional", ["YANDEX_WEBMASTER_TOKEN", "YANDEX_METRIKA_TOKEN"]),
]


def main() -> int:
    print("=== credentials status (.env) ===\n")
    for title, keys in GROUPS:
        print(f"[{title}]")
        for k in keys:
            v = (os.getenv(k) or "").strip()
            print(f"  {k}: {'OK' if v else '—'}")
        print()
    print("Секреты не выводятся. Инструкция: checklists/credentials.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
