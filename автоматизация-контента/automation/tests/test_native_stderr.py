import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_windowless import run_hidden


@unittest.skipUnless(os.name=='nt','Windows PowerShell native stderr behavior')
class NativeStderrTests(unittest.TestCase):
    def run_fixture(self,exit_code):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        automation=root/'automation';automation.mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1]/'run-windows.ps1',automation/'run-windows.ps1')
        scripts=root/'.venv/Scripts';scripts.mkdir(parents=True)
        shutil.copyfile(sys.executable,scripts/'python.exe')
        shutil.copyfile(Path(sys.prefix)/'pyvenv.cfg',root/'.venv/pyvenv.cfg')
        code="import sys\nsys.stderr.write('warning: ordinary native stderr\\n')\nprint('native-finished',flush=True)\nraise SystemExit("+str(exit_code)+")\n"
        (automation/'run_local.py').write_text(code,encoding='utf-8')
        ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        with (root/'host.log').open('wb') as log:
            result=run_hidden([str(ps),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(automation/'run-windows.ps1'),'-RuntimeRoot',str(root)],stdout=log)
        output=(root/'logs/mkekspert-content.log').read_text(encoding='utf-8-sig')
        return result,output

    def test_successful_native_stderr_does_not_abort_publisher(self):
        result,log=self.run_fixture(0)
        self.assertEqual(result,0,log)
        self.assertIn('warning: ordinary native stderr',log)
        self.assertIn('native-finished',log)

    def test_nonzero_native_exit_still_fails_and_keeps_log(self):
        result,log=self.run_fixture(23)
        self.assertNotEqual(result,0)
        self.assertIn('native-finished',log)
