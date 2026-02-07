@echo off
title AI Radio Station - KPXL Nocturnal Radio
echo.
echo  ============================================
echo   KPXL Nocturnal Radio - AI Radio Station
echo  ============================================
echo.

:: Start backend
echo Starting backend...
start "AI Radio Backend" /D "%~dp0backend" cmd /c "python main.py"

:: Wait for backend to start
timeout /t 3 /nobreak > nul

:: Start frontend
echo Starting frontend...
start "AI Radio Frontend" /D "%~dp0frontend" cmd /c "npm run dev"

:: Wait and open browser
timeout /t 3 /nobreak > nul
echo.
echo Opening http://localhost:5173 ...
start http://localhost:5173

echo.
echo Radio station is running!
echo Close this window to stop all services.
echo.
pause
