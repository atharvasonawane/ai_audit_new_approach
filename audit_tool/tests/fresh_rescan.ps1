param(
    [switch]$ResetOnly,
    [switch]$SkipAI,
    [switch]$StartReport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Resolve-PythonExe {
    $venvPython = Join-Path $PSScriptRoot "audit_tool\venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }
    return "python"
}

function Stop-ListeningProcesses {
    param(
        [int[]]$Ports
    )

    $stopped = @{}
    foreach ($port in $Ports) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop
        } catch {
            continue
        }

        foreach ($connection in $connections) {
            $pid = $connection.OwningProcess
            if ($pid -and -not $stopped.ContainsKey($pid)) {
                try {
                    $process = Get-Process -Id $pid -ErrorAction Stop
                    Write-Host "Stopping process on port ${port}: PID $pid ($($process.ProcessName))" -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    $stopped[$pid] = $true
                } catch {
                    Write-Warning "Failed to stop PID $pid on port ${port}: $($_.Exception.Message)"
                }
            }
        }
    }
}

function Remove-Artifacts {
    $artifactPaths = @(
        "audit_history.db",
        "audit_history.db-shm",
        "audit_history.db-wal",
        "scan.log",
        "report\frontend\public\graph.json",
        "report\frontend\debug.log"
    )

    foreach ($relativePath in $artifactPaths) {
        $fullPath = Join-Path $PSScriptRoot $relativePath
        if (Test-Path $fullPath) {
            Remove-Item -LiteralPath $fullPath -Force -ErrorAction Stop
            Write-Host "Deleted $relativePath" -ForegroundColor Green
        }
    }
}

function Assert-ArtifactsRemoved {
    $artifactPatterns = @(
        "audit_history.db*",
        "scan.log",
        "report\frontend\public\graph.json",
        "report\frontend\debug.log"
    )

    $remaining = @()
    foreach ($pattern in $artifactPatterns) {
        $remaining += Get-ChildItem -Path (Join-Path $PSScriptRoot $pattern) -ErrorAction SilentlyContinue
    }

    if ($remaining.Count -gt 0) {
        $remainingPaths = $remaining | ForEach-Object { $_.FullName }
        throw "Cleanup verification failed. Remaining artifacts: $($remainingPaths -join ', ')"
    }

    Write-Host "Cleanup verification passed." -ForegroundColor Green
}

function Show-ConfigSummary {
    $configPath = Join-Path $PSScriptRoot "audit_tool\config\project_config.yaml"
    $envPath = Join-Path $PSScriptRoot ".env"

    Write-Step "Config summary"

    if (Test-Path $configPath) {
        $configLines = Get-Content -LiteralPath $configPath
        $projectName = ""
        $basePath = ""
        $dbPath = ""

        for ($i = 0; $i -lt $configLines.Count; $i++) {
            $line = $configLines[$i]
            if (-not $projectName) {
                $projectMatch = [regex]::Match($line, '^project_name:\s*(.+)$')
                if ($projectMatch.Success) {
                    $projectName = $projectMatch.Groups[1].Value.Trim()
                }
            }
            if (-not $basePath) {
                $baseMatch = [regex]::Match($line, '^base_path:\s*(.+)$')
                if ($baseMatch.Success) {
                    $basePath = $baseMatch.Groups[1].Value.Trim()
                }
            }
            if ($line -match '^db:\s*$' -and ($i + 1) -lt $configLines.Count) {
                $dbMatch = [regex]::Match($configLines[$i + 1], '^\s*path:\s*(.+)$')
                if ($dbMatch.Success) {
                    $dbPath = $dbMatch.Groups[1].Value.Trim()
                }
            }
        }

        if ($projectName) { Write-Host "project_name: $projectName" }
        if ($basePath) { Write-Host "base_path: $basePath" }
        if ($dbPath) { Write-Host "db.path: $dbPath" }
    }

    if (Test-Path $envPath) {
        $envText = Get-Content -LiteralPath $envPath -Raw
        $llmBaseUrl = [regex]::Match($envText, '(?m)^OPENWEBUI_BASE_URL=(.+)$').Groups[1].Value.Trim()
        $llmModel = [regex]::Match($envText, '(?m)^LLM_MODEL=(.+)$').Groups[1].Value.Trim()

        if ($llmBaseUrl) { Write-Host "OPENWEBUI_BASE_URL: $llmBaseUrl" }
        if ($llmModel) { Write-Host "LLM_MODEL: $llmModel" }
    }
}

function Invoke-StepCommand {
    param(
        [string]$Label,
        [string]$Executable,
        [string[]]$Arguments
    )

    Write-Step $Label
    Write-Host "$Executable $($Arguments -join ' ')" -ForegroundColor DarkGray
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Invoke-DbCheck {
    param(
        [string]$Label,
        [string]$PythonExe,
        [string]$Code
    )

    Write-Step $Label
    & $PythonExe -c $Code
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$pythonExe = Resolve-PythonExe

Write-Step "Stopping report servers on common ports"
Stop-ListeningProcesses -Ports @(5000, 5173, 3000)

Write-Step "Deleting previous scan artifacts"
Remove-Artifacts
Assert-ArtifactsRemoved

Show-ConfigSummary

if ($ResetOnly) {
    Write-Step "Reset complete"
    Write-Host "Fresh reset completed. No scan phases were executed." -ForegroundColor Green
    exit 0
}

Invoke-StepCommand -Label "Scout phase" -Executable $pythonExe -Arguments @("audit_tool\run_audit.py", "--scout-only")
Invoke-DbCheck -Label "Scout verification" -PythonExe $pythonExe -Code "import sqlite3; c=sqlite3.connect('audit_history.db'); print('Files:', c.execute('select count(*) from vue_files').fetchone()[0]); print('ESLint:', c.execute('select count(*) from file_flags').fetchone()[0]); print('A11y:', c.execute('select count(*) from accessibility_defects').fetchone()[0])"

Invoke-StepCommand -Label "Dependency graph phase" -Executable $pythonExe -Arguments @("audit_tool\run_audit.py", "--graph-only")
Invoke-DbCheck -Label "Dependency graph verification" -PythonExe $pythonExe -Code "import sqlite3; c=sqlite3.connect('audit_history.db'); print('Relationships:', c.execute('select count(*) from component_relationships').fetchone()[0]); print('Dependency metrics:', c.execute('select count(*) from dependency_metrics').fetchone()[0])"

if (-not $SkipAI) {
    Invoke-StepCommand -Label "AI phase" -Executable $pythonExe -Arguments @("audit_tool\run_audit.py", "--ai-only")
    Invoke-DbCheck -Label "AI verification" -PythonExe $pythonExe -Code "import sqlite3; c=sqlite3.connect('audit_history.db'); print('AI issues:', c.execute('select count(*) from ai_issues').fetchone()[0]); row=c.execute('select status from audit_runs order by id desc limit 1').fetchone(); print(row[0] if row else 'no_runs')"
} else {
    Write-Step "AI phase skipped"
    Write-Host "Skipped AI analysis by request." -ForegroundColor Yellow
}

if ($StartReport) {
    Invoke-StepCommand -Label "Report phase" -Executable $pythonExe -Arguments @("audit_tool\run_audit.py", "--report-only")
} else {
    Write-Step "Rescan complete"
    Write-Host "Fresh rescan completed. Start the report later with:" -ForegroundColor Green
    Write-Host "$pythonExe audit_tool\run_audit.py --report-only" -ForegroundColor DarkGray
}
