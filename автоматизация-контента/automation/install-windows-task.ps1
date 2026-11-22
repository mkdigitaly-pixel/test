param(
    [Parameter(Mandatory=$true)][string]$RuntimeRoot
)
$ErrorActionPreference = 'Stop'
$taskName = 'mkekspert-content'
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) { throw 'Task already exists; inspect it instead of creating a duplicate' }
$checkout = Join-Path $RuntimeRoot 'repo'
$projects = @(Get-ChildItem -LiteralPath $checkout -Directory | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'automation\run-windows.ps1') })
if ($projects.Count -ne 1) { throw 'Expected exactly one content project with the Windows launcher' }
$entry = Join-Path $projects[0].FullName 'automation\run-windows.ps1'
$quote = [char]34
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File ' + $quote + $entry + $quote + ' -RuntimeRoot ' + $quote + $RuntimeRoot + $quote
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -Disable -StartWhenAvailable -RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'mkekspert: local publisher; only enabled after server cron is disabled' | Select-Object TaskName,State
