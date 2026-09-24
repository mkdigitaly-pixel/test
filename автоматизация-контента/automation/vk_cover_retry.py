#!/usr/bin/env python3
"""VK cover retry — disabled while VK_PHOTOS=manual."""

from __future__ import annotations

import sys

from publish import load_env, vk_photos_allowed, vk_photos_mode


def main() -> None:
    load_env()
    if not vk_photos_allowed():
        print(
            f"VK photos mode={vk_photos_mode()} — no upload probes. "
            "Maria attaches covers manually.",
            flush=True,
        )
        sys.exit(0)
    print(
        "VK_PHOTOS=auto: use python publish.py vk-attach-cover <post_id> <id>",
        flush=True,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
