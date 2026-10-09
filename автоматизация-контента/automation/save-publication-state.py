#!/usr/bin/env python3
"""Back up publication receipts without staging credentials or unrelated work."""
import subprocess
import yaml
from pathlib import Path

root = Path(__file__).resolve().parent.parent
repo = root.parent
paths = [str((root / 'queue' / name).relative_to(repo)) for name in (
    'posting-schedule.yaml', 'publish-queue.yaml', 'posts-queue.yaml', 'covers-inbox.yaml'
) if (root / 'queue' / name).exists()]
inbox_file = root / 'queue' / 'covers-inbox.yaml'
if inbox_file.exists():
    inbox = yaml.safe_load(inbox_file.read_text(encoding='utf-8')) or {}
    for item in inbox.get('items', []):
        rel = str(item.get('brief') or '')
        brief = (root / rel).resolve()
        if rel.startswith('briefs/covers/') and brief.suffix == '.md' and (root / 'briefs' / 'covers').resolve() in brief.parents and brief.is_file():
            paths.append(str(brief.relative_to(repo)))
paths = list(dict.fromkeys(paths))
status = subprocess.check_output(['git', 'status', '--porcelain', '--'] + paths, cwd=repo, text=True)
if status.strip():
    subprocess.run(['git', 'add', '--'] + paths, cwd=repo, check=True)
    subprocess.run(['git', 'commit', '--only', '-m', 'chore(content): save publication receipts', '--'] + paths, cwd=repo, check=True)
    subprocess.run(['git', 'push'], cwd=repo, check=True, timeout=120)
