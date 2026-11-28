import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_windowless import run_hidden

PROBE = r"""import ctypes,json,subprocess,sys
from ctypes import wintypes
from pathlib import Path
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
user=ctypes.WinDLL('user32',use_last_error=True)
kernel.GetConsoleWindow.restype=wintypes.HWND
user.IsWindowVisible.argtypes=[wintypes.HWND]
user.IsWindowVisible.restype=wintypes.BOOL
handle=kernel.GetConsoleWindow()
Path(sys.argv[1]).write_text(json.dumps({'handle':int(handle or 0),'visible':bool(user.IsWindowVisible(handle))}),encoding='utf-8')
if len(sys.argv)>2:
    subprocess.run([sys.executable,__file__,sys.argv[2]],check=True)
"""


@unittest.skipUnless(os.name == 'nt', 'Windows console startup behavior')
class WindowlessLauncherTests(unittest.TestCase):
    def test_python_and_descendant_share_an_initially_hidden_console(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'папка с пробелами'
            base.mkdir()
            probe=base/'probe.py';probe.write_text(PROBE,encoding='utf-8')
            parent=base/'parent.json';child=base/'child.json'
            self.assertEqual(run_hidden([sys.executable,str(probe),str(parent),str(child)]),0)
            a=json.loads(parent.read_text());b=json.loads(child.read_text())
            self.assertFalse(a['visible']);self.assertFalse(b['visible'])
            self.assertNotEqual(a['handle'],0)
            self.assertEqual(a['handle'],b['handle'])

    def test_powershell_children_remain_hidden_and_exit_code_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            probe=base/'probe.py';probe.write_text(PROBE,encoding='utf-8')
            parent=base/'parent.json';child=base/'child.json'
            quote=lambda value:"'"+str(value).replace("'","''")+"'"
            script=base/'run.ps1'
            script.write_text('& '+quote(sys.executable)+' '+quote(probe)+' '+quote(parent)+' '+quote(child)+'\nexit 7\n',encoding='utf-8-sig')
            ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
            self.assertEqual(run_hidden([str(ps),'-NoProfile','-NonInteractive','-File',str(script)]),7)
            a=json.loads(parent.read_text());b=json.loads(child.read_text())
            self.assertFalse(a['visible']);self.assertFalse(b['visible'])
            self.assertEqual(a['handle'],b['handle'])


if __name__ == '__main__':
    unittest.main()
