import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('receipt_backup', Path(__file__).resolve().parents[1] / 'save-publication-state.py')
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class ReceiptBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo = base / 'local repo'
        self.remote = base / 'remote.git'
        self.root = self.repo / 'content'
        self.root.mkdir(parents=True)
        (self.root / 'queue').mkdir()
        (self.root / 'queue/posts-queue.yaml').write_text('items: []\n', encoding='utf-8')
        self.git('init', '--bare', str(self.remote), cwd=base)
        self.git('init', '-b', backup.EXPECTED_BRANCH)
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('add', '.')
        self.git('commit', '-m', 'seed')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', backup.EXPECTED_BRANCH)

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', *args], cwd=cwd or self.repo, text=True, stderr=subprocess.DEVNULL).strip()

    def test_clean_worktree_retries_saved_commit_after_push_failure(self):
        queue = self.root / 'queue/posts-queue.yaml'
        queue.write_text('items:\n- id: sample\n  message_id: 123\n', encoding='utf-8')
        original_run = subprocess.run

        def fail_push(args, **kwargs):
            if args[:2] == ['git', 'push']:
                raise subprocess.CalledProcessError(1, args)
            return original_run(args, **kwargs)

        with patch.object(backup.subprocess, 'run', side_effect=fail_push):
            with self.assertRaises(subprocess.CalledProcessError):
                backup.save_state(self.root)
        self.assertEqual(self.git('status', '--porcelain'), '')
        saved_head = self.git('rev-parse', 'HEAD')
        self.assertNotEqual(saved_head, self.git('rev-parse', '@{upstream}'))
        backup.save_state(self.root)
        self.assertEqual(saved_head, self.git('rev-parse', '@{upstream}'))
        self.assertEqual(saved_head, self.git('--git-dir=' + str(self.remote), 'rev-parse', 'refs/heads/' + backup.EXPECTED_BRANCH))

    def test_receipt_commit_excludes_secrets_and_unrelated_staged_work(self):
        (self.root / '.env').write_text('TOKEN=private-fixture\n', encoding='utf-8')
        (self.repo / 'unrelated.txt').write_text('unfinished work\n', encoding='utf-8')
        self.git('add', 'unrelated.txt')
        (self.root / 'queue/posts-queue.yaml').write_text('items:\n- id: sample\n  message_id: 456\n', encoding='utf-8')
        backup.save_state(self.root)
        committed = self.git('ls-tree', '-r', '--name-only', 'HEAD').splitlines()
        self.assertNotIn('content/.env', committed)
        self.assertNotIn('unrelated.txt', committed)
        self.assertEqual(self.git('diff', '--cached', '--name-only'), 'unrelated.txt')


if __name__ == '__main__':
    unittest.main()
