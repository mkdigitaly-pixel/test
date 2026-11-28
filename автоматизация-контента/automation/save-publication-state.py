#!/usr/bin/env python3
"""Save public receipts and retry a previously interrupted push without resending."""
import subprocess
from pathlib import Path

import yaml

EXPECTED_BRANCH = 'cursor/project-passport-8631'


def receipt_paths(root):
    repo = root.parent
    paths = [(root / 'queue' / name).relative_to(repo).as_posix() for name in (
        'posting-schedule.yaml', 'publish-queue.yaml', 'posts-queue.yaml', 'covers-inbox.yaml'
    ) if (root / 'queue' / name).exists()]
    inbox_file = root / 'queue' / 'covers-inbox.yaml'
    if inbox_file.exists():
        inbox = yaml.safe_load(inbox_file.read_text(encoding='utf-8')) or {}
        for item in inbox.get('items', []):
            rel = str(item.get('brief') or '')
            brief = (root / rel).resolve()
            if rel.startswith('briefs/covers/') and brief.suffix == '.md' and (root / 'briefs' / 'covers').resolve() in brief.parents and brief.is_file():
                paths.append(brief.relative_to(repo).as_posix())
    return list(dict.fromkeys(paths))


def save_state(root):
    root = Path(root).resolve()
    repo = root.parent
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=repo, text=True).strip()
    if branch != EXPECTED_BRANCH:
        raise RuntimeError('Publication receipts must stay on the approved working branch')
    paths = receipt_paths(root)
    status = subprocess.check_output(['git', 'status', '--porcelain', '--'] + paths, cwd=repo, text=True)
    if status.strip():
        subprocess.run(['git', 'add', '--'] + paths, cwd=repo, check=True)
        subprocess.run(['git', 'commit', '--only', '-m', 'chore(content): save publication receipts', '--'] + paths, cwd=repo, check=True)
    # A failed push leaves a clean worktree. Retry that saved commit on the next run.
    ahead = int(subprocess.check_output(['git', 'rev-list', '--count', '@{upstream}..HEAD'], cwd=repo, text=True).strip())
    if ahead:
        subprocess.run(['git', 'push'], cwd=repo, check=True, timeout=120)


if __name__ == '__main__':
    save_state(Path(__file__).resolve().parent.parent)
