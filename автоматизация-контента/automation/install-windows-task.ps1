param(
    [Parameter(Mandatory=$true)][string]$RuntimeRoot
)
$ErrorActionPreference = 'Stop'
$taskName = 'mkekspert-content'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) { throw 'Task already exists; inspect it instead of creating a duplicate' }
$checkout = Join-Path $RuntimeRoot 'repo'
$projects = @(Get-ChildItem -LiteralPath $checkout -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'automation\run_windowless.py') })
if ($projects.Count -ne 1) { throw 'Expected exactly one content project with the Windows launcher' }
$entry = Join-Path $projects[0].FullName 'automation\run_windowless.py'
$quote = [char]34
$arguments = $quote + $entry + $quote + ' --runtime-root ' + $quote + $RuntimeRoot + $quote
$pythonw = Join-Path $RuntimeRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Windowless Python runtime is missing' }
$action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $RuntimeRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$settings = New-ScheduledTaskSettingsSet -Disable -StartWhenAvailable -RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger,$logonTrigger) -Settings $settings -Principal $principal -Description 'mkekspert: local publisher; only enabled after server cron is disabled' | Select-Object TaskName,State
