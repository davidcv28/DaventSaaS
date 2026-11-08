# Lanzador de olas del plan de webs profesionales.
# Uso:
#   .\tools\ola.ps1 -Wave 1                 # abre 5 pestanas, una por track, ya con su tarea
#   .\tools\ola.ps1 -Wave 2                 # track F (integracion)
#   .\tools\ola.ps1 -Wave 3                 # tracks G1-G4 (fixes por patron)
#   .\tools\ola.ps1 -Wave 4                 # track Z (limpieza, dry-run + confirmacion)
#   .\tools\ola.ps1 -Wave 1 -Only a,b       # solo esos tracks
#   .\tools\ola.ps1 -Wave 1 -Mode batch     # sin ventanas: procesos en background con log
#   .\tools\ola.ps1 -Wave 1 -DryRun         # solo muestra que haria
#
# Los roles viven en .devin/agents/track-*.md (fuente unica). Este script les quita el
# frontmatter y arranca `devin --prompt-file` con el resto.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet(1, 2, 3, 4)][int]$Wave,
    [ValidateSet('tabs', 'batch')][string]$Mode = 'tabs',
    [string[]]$Only = @(),
    [ValidateSet('accept-edits', 'normal', 'dangerous')][string]$PermissionMode = 'accept-edits',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$repo       = Split-Path -Parent $PSScriptRoot
$agentsDir  = Join-Path $repo '.devin\agents'
$promptsDir = Join-Path $repo '.devin\prompts'
$logsDir    = Join-Path $repo '.devin\logs'

$waveTracks = @{
    1 = @('a', 'b', 'c', 'd', 'e')
    2 = @('f')
    3 = @('g1', 'g2', 'g3', 'g4')
    4 = @('z')
}

$ids = if ($Only.Count -gt 0) { $Only } else { $waveTracks[$Wave] }

if (-not (Test-Path -LiteralPath $agentsDir)) { throw "No existe $agentsDir" }
if (-not $DryRun) {
    New-Item -ItemType Directory -Force -Path $promptsDir, $logsDir | Out-Null
}

# 1. Materializar el prompt de cada track (body del .md, sin frontmatter).
$prompts = @{}
foreach ($id in $ids) {
    $src = Join-Path $agentsDir "track-$id.md"
    if (-not (Test-Path -LiteralPath $src)) { throw "No existe el rol: $src" }

    $lines  = Get-Content -LiteralPath $src
    $fences = @(for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].Trim() -eq '---') { $i } })
    $start  = if ($fences.Count -ge 2) { $fences[1] + 1 } else { 0 }
    $body   = (($lines[$start..($lines.Count - 1)]) -join "`r`n").Trim()

    $out = Join-Path $promptsDir "track-$id.txt"
    if (-not $DryRun) {
        [System.IO.File]::WriteAllText($out, $body, (New-Object System.Text.UTF8Encoding($false)))
    }
    $prompts[$id] = $out
    Write-Host "[$id] $src -> $out" -ForegroundColor DarkGray
}

# 2. Lanzar.
foreach ($id in $ids) {
    $prompt = $prompts[$id]

    if ($Mode -eq 'tabs') {
        $wtArgs = @(
            '-w', '0', 'new-tab',
            '--title', "`"track-$id`"",
            '-d', "`"$repo`"",
            'devin.exe', '--prompt-file', "`"$prompt`""
        )
        if ($DryRun) {
            Write-Host ("wt.exe " + ($wtArgs -join ' ')) -ForegroundColor Cyan
        } else {
            Start-Process -FilePath 'wt.exe' -ArgumentList $wtArgs | Out-Null
            Start-Sleep -Milliseconds 500
        }
    }
    else {
        $log   = Join-Path $logsDir "track-$id.log"
        $inner = "& devin.exe -p --permission-mode $PermissionMode --respect-workspace-trust false --prompt-file `"$prompt`" *> `"$log`""
        if ($DryRun) {
            Write-Host ("powershell -NoProfile -Command " + $inner) -ForegroundColor Cyan
        } else {
            Start-Process -FilePath 'powershell.exe' `
                -ArgumentList @('-NoProfile', '-Command', $inner) `
                -WorkingDirectory $repo -WindowStyle Minimized | Out-Null
        }
    }
}

Write-Host ''
if ($DryRun) {
    Write-Host 'DRY RUN: no se lanzo nada.' -ForegroundColor Yellow
} elseif ($Mode -eq 'tabs') {
    Write-Host "Lanzados: $($ids -join ', ') (una pestana por track)." -ForegroundColor Green
    Write-Host 'Cada pestana trabaja sobre su scope. Al terminar: git status, verificar y commitear.' -ForegroundColor DarkGray
} else {
    Write-Host "Lanzados en background: $($ids -join ', ')." -ForegroundColor Green
    Write-Host "Logs: $logsDir" -ForegroundColor DarkGray
}
