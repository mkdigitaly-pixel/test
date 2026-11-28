"""Start the existing Windows publisher without a visible console at startup."""
import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_hidden(command, *, cwd=None, stdout=None):
    if os.name != 'nt':
        raise RuntimeError('The windowless launcher is only for Windows')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    # Allocate an initially hidden console; descendants inherit it instead of
    # opening their own console when Python/Git/SSH start.
    return subprocess.run(
        command, cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=stdout if stdout is not None else subprocess.DEVNULL,
        stderr=subprocess.STDOUT, startupinfo=startup,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    ).returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    runtime = args.runtime_root.resolve()
    expected = runtime / 'repo' / 'автоматизация-контента' / 'automation' / 'run_windowless.py'
    if Path(__file__).resolve() != expected.resolve():
        raise RuntimeError('Wrong checkout for the selected runtime root')
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    command = [str(powershell), '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
               '-ExecutionPolicy', 'Bypass', '-File', str(Path(__file__).with_name('run-windows.ps1')),
               '-RuntimeRoot', str(runtime)]
    if args.dry_run:
        command.append('-DryRun')
    logs = runtime / 'logs'
    logs.mkdir(exist_ok=True)
    with (logs / 'launcher-errors.log').open('ab') as log:
        try:
            result = run_hidden(command, cwd=runtime, stdout=log)
            if result:
                log.write((datetime.now(timezone.utc).isoformat() + ' publisher exit ' + str(result) + '\n').encode('utf-8'))
            return result
        except Exception as exc:
            log.write((datetime.now(timezone.utc).isoformat() + ' launcher failure: ' + str(exc) + '\n').encode('utf-8'))
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
