#!/usr/bin/env python3
"""Back up publication receipts without staging credentials or unrelated work."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
repo = root.parent
paths = [str((root / 'queue' / name).relative_to(repo)) for name in (
    'posting-schedule.yaml', 'publish-queue.yaml', 'posts-queue.yaml', 'covers-inbox.yaml'
) if (root / 'queue' / name).exists()]
status = subprocess.check_output(['git', 'status', '--porcelain', '--'] + paths, cwd=repo, text=True)
if status.strip():
    subprocess.run(['git', 'add', '--'] + paths, cwd=repo, check=True)
    subprocess.run(['git', 'commit', '--only', '-m', 'chore(content): save publication receipts', '--'] + paths, cwd=repo, check=True)
    subprocess.run(['git', 'push'], cwd=repo, check=True, timeout=120)
