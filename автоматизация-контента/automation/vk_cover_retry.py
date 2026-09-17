#!/usr/bin/env python3
"""Retry attaching correct VK covers when flood control lifts."""

from __future__ import annotations

import os
import time
import traceback
from pathlib import Path

import requests

from publish import (
    find_queue_item,
    load_env,
    load_queue,
    load_plain_post,
    publish_vk,
    replace_dzen_url,
    resolve_cover_path,
    resolve_path,
    resolve_vk_group_id,
    teaser_vk_path,
    upload_vk_wall_photo,
    vk_api,
)

LOG = Path("/tmp/vk-cover-retry.log")
# Актуальные посты с recycle-фото; правильные обложки — когда спадёт flood.
JOBS = (
    ("autotarget-b2b", 219),
    ("no-leads-direct", 220),
)
SLEEP_SEC = 60 * 60


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    load_env()
    user = os.environ["VK_USER_TOKEN"].strip()
    comm = os.environ["VK_ACCESS_TOKEN"].strip()
    gid = resolve_vk_group_id(comm, os.environ["VK_GROUP_ID"])
    attempt = 0
    while True:
        attempt += 1
        try:
            vk_api("photos.getWallUploadServer", user, group_id=gid)
        except Exception as exc:
            log(f"attempt {attempt}: still blocked: {exc}")
            time.sleep(SLEEP_SEC)
            continue
        log(f"attempt {attempt}: upload unlocked")
        items = load_queue()
        ok_all = True
        for cid, post_id in JOBS:
            try:
                item = find_queue_item(items, cid)
                cover = resolve_cover_path(item, vk=True) or resolve_cover_path(item)
                if not cover or not cover.exists():
                    raise RuntimeError(f"no cover for {cid}")
                att = upload_vk_wall_photo(user, gid, cover)
                text = replace_dzen_url(
                    load_plain_post(resolve_path(teaser_vk_path(item))),
                    item.get("dzen_url", ""),
                )
                resp = requests.post(
                    "https://api.vk.com/method/wall.edit",
                    data={
                        "access_token": user,
                        "v": "5.199",
                        "owner_id": -gid,
                        "post_id": post_id,
                        "message": text,
                        "attachments": att,
                    },
                    timeout=60,
                ).json()
                if "error" in resp:
                    log(f"{cid} wall.edit fail {resp['error']} -> wall.post")
                    result = publish_vk(
                        text, comm, str(gid), cover=cover, user_token=user
                    )
                    log(f"{cid} new post {result}")
                else:
                    log(f"{cid} edited post {post_id} with {att}")
            except Exception as exc:
                ok_all = False
                log(f"{cid} FAIL {exc}\n{traceback.format_exc()}")
                time.sleep(SLEEP_SEC)
                break
        if ok_all:
            log("done all")
            return


if __name__ == "__main__":
    main()
