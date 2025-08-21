@echo off
REM Keiba Analysis System Stop Script for Windows

echo ======================================
echo   Stopping Keiba Analysis System
echo ======================================

REM Kill Node.js processes (Frontend)
echo Stopping frontend...
taskkill /F /IM node.exe 2>nul

REM Kill Python processes (Backend)
echo Stopping backend services...
taskkill /F /IM python.exe 2>nul

REM Stop Docker services
echo Stopping Docker services...
docker-compose --profile tools --profile app --profile worker down

echo.
echo All services stopped.
pause