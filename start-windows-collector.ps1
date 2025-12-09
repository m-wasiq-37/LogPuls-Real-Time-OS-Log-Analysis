$scriptPath = Join-Path $PSScriptRoot "agent\windows_collector_server.py"
if (Test-Path $scriptPath) {
    Write-Host "Starting Windows Log Collector Server..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    python $scriptPath
} else {
    Write-Host "Error: Windows collector script not found at $scriptPath" -ForegroundColor Red
    Write-Host "Please ensure the file exists and Python is installed." -ForegroundColor Yellow
    pause
    exit 1
}
