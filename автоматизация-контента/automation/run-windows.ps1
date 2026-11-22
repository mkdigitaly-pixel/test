param(
    [Parameter(Mandatory=$true)][string]$RuntimeRoot,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$gitCandidates = @('C:\Program Files\Git\cmd\git.exe')
$gitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if ($gitCommand) { $gitCandidates += $gitCommand.Source }
$packages = Get-AppxPackage -Name 'OpenAI.CodexPrimaryRuntime*' -ErrorAction SilentlyContinue | Sort-Object Version -Descending
foreach ($package in $packages) {
    $gitCandidates += Join-Path $package.InstallLocation 'dependencies\native\git\cmd\git.exe'
}
$gitExe = $gitCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $gitExe) { throw 'Git is not installed or cannot be located' }
$env:PATH = (Split-Path -Parent $gitExe) + ';' + $env:PATH
$pythonExe = Join-Path $RuntimeRoot '.venv\Scripts\python.exe'
$entry = Join-Path $PSScriptRoot 'run_local.py'
$logDir = Join-Path $RuntimeRoot 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logPath = Join-Path $logDir 'mkekspert-content.log'
if ((Test-Path -LiteralPath $logPath) -and (Get-Item -LiteralPath $logPath).Length -gt 10MB) {
    Move-Item -LiteralPath $logPath -Destination (Join-Path $logDir ('mkekspert-content-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log'))
}
$argsList = @($entry, '--runtime-root', $RuntimeRoot)
if ($DryRun) { $argsList += '--dry-run' }
& $pythonExe @argsList 2>&1 | Out-File -LiteralPath $logPath -Append -Encoding utf8
$runExitCode = $LASTEXITCODE
if ($runExitCode -ne 0) { throw "Local publisher exited with code $runExitCode; see $logPath" }
