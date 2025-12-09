@echo off
title Windows Log Collector Server
echo ========================================
echo   LogPuls - Windows Log Collector
echo ========================================
echo.
cd /d "%~dp0"
if exist "agent\windows_collector_server.py" (
    echo Starting Windows Log Collector Server...
    echo Press Ctrl+C to stop the server
    echo.
    python agent\windows_collector_server.py
    if errorlevel 1 (
        echo.
        echo Error: Failed to start Windows collector server
        echo Please ensure Python and pywin32 are installed
        echo.
        pause
    )
) else (
    echo Error: Windows collector script not found
    echo Expected location: agent\windows_collector_server.py
    echo.
    pause
    exit /b 1
)

