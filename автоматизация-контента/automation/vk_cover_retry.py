#!/usr/bin/env python3
"""Retry attaching correct VK covers when flood control lifts.

По решению от 2026-09-19: до VK_TEXT_ONLY_UNTIL (по умолчанию 2026-10-19)
не трогаем user API / загрузку фото. Скрипт сразу выходит.
"""

from __future__ import annotations

import sys

from publish import load_env, vk_photos_allowed, vk_photos_paused_until


def main() -> None:
    load_env()
    if not vk_photos_allowed():
        until = vk_photos_paused_until()
        print(
            f"VK photos paused until {until.date().isoformat()} — no upload probes.",
            flush=True,
        )
        sys.exit(0)
    print(
        "VK photos allowed again, but hourly retry loop is disabled. "
        "Use: python publish.py vk-attach-cover <id> --post-id N",
        flush=True,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
