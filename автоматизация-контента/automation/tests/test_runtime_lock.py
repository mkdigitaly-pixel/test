import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_lock import exclusive_lock

AUTOMATION = str(Path(__file__).resolve().parents[1])


class RuntimeLockTests(unittest.TestCase):
    def contender(self, path):
        code = """import sys
sys.path.insert(0, sys.argv[1])
from runtime_lock import exclusive_lock, LockBusy
try:
    with exclusive_lock(sys.argv[2]):
        pass
except LockBusy:
    raise SystemExit(73)
"""
        return subprocess.run([sys.executable, "-c", code, AUTOMATION, str(path)], capture_output=True, text=True, timeout=8)

    def test_lock_excludes_another_process_and_can_be_reacquired(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "очередь с пробелами.lock"
            with exclusive_lock(path):
                blocked = self.contender(path)
                self.assertEqual(blocked.returncode, 73, blocked.stderr)
            acquired = self.contender(path)
            self.assertEqual(acquired.returncode, 0, acquired.stderr)

    def test_exception_releases_lock_for_another_process(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "queue.lock"
            with self.assertRaisesRegex(ValueError, "test failure"):
                with exclusive_lock(path):
                    raise ValueError("test failure")
            acquired = self.contender(path)
            self.assertEqual(acquired.returncode, 0, acquired.stderr)


if __name__ == "__main__":
    unittest.main()
