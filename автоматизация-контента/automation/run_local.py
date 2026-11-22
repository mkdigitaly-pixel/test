"""Run the existing schedule on a persistent local checkout; disabled until cutover."""
import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import publish as pub
from runtime_lock import LockBusy, exclusive_lock


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    runtime = args.runtime_root.resolve()
    expected = runtime / "repo" / "автоматизация-контента"
    if pub.ROOT.resolve() != expected.resolve():
        raise SystemExit("Wrong checkout for the selected runtime root")
    state_path = runtime / "private" / "runtime-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not args.dry_run and not state.get("enabled"):
        print("Local publisher is disabled; no sends")
        return 0
    if state.get("hostname") != socket.gethostname():
        raise SystemExit("Runtime belongs to another computer")
    pub.ENV_FILE = runtime / "private" / "automation.env"
    if not pub.ENV_FILE.is_file():
        raise SystemExit("Private runtime configuration is missing")
    pub.load_env()
    if pub.vk_photos_mode() != "manual":
        raise SystemExit("VK_PHOTOS must remain manual")
    os.chdir(pub.ROOT)
    try:
        with exclusive_lock(pub.ROOT / "queue" / ".launcher.lock"):
            print(datetime.now(timezone.utc).isoformat(), "local schedule", "dry-run" if args.dry_run else "live")
            try:
                return pub.cmd_schedule_run(argparse.Namespace(dry_run=args.dry_run, date=None, force=False))
            finally:
                if not args.dry_run:
                    subprocess.run([sys.executable, str(pub.ROOT / "automation" / "save-publication-state.py")], check=True)
    except LockBusy:
        print("Local publisher is already running; skipped")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(pub.redacted_error(exc), file=sys.stderr)
        raise SystemExit(1)
