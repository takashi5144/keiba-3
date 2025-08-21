@echo off
REM Keiba Analysis System Startup Script for Windows

echo ======================================
echo   Keiba Analysis System Startup
echo ======================================

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration and run this script again.
    exit /b 1
)

REM Start Docker services
echo.
echo Starting Docker services...
docker-compose up -d postgres redis

REM Wait for services to be ready
echo Waiting for services to be ready...
timeout /t 10 /nobreak > nul

REM Run database migrations
echo.
echo Running database migrations...
cd backend
call poetry run alembic upgrade head
cd ..

REM Create logs directory
if not exist logs mkdir logs

REM Start backend services
echo.
echo Starting backend services...

REM Start API server
cd backend
start /b cmd /c "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/api.log 2>&1"
echo API server started
cd ..

REM Wait for API to be ready
timeout /t 5 /nobreak > nul

REM Start Celery worker
cd backend
start /b cmd /c "poetry run celery -A app.core.celery_app worker --loglevel=info --pool=solo > ../logs/celery-worker.log 2>&1"
echo Celery worker started

REM Start Celery beat
start /b cmd /c "poetry run celery -A app.core.celery_app beat --loglevel=info > ../logs/celery-beat.log 2>&1"
echo Celery beat started
cd ..

REM Start frontend
echo.
echo Starting frontend...
cd frontend
start /b cmd /c "npm run dev > ../logs/frontend.log 2>&1"
echo Frontend started
cd ..

REM Wait for all services
timeout /t 10 /nobreak > nul

REM Optional: Start monitoring tools
echo.
set /p MONITORING="Start monitoring tools (pgAdmin, Flower)? (y/n): "
if /i "%MONITORING%"=="y" (
    docker-compose --profile tools up -d
    echo Monitoring tools started
)

echo.
echo ======================================
echo   System Started Successfully!
echo ======================================
echo.
echo Services available at:
echo   - Frontend:    http://localhost:3000
echo   - Backend API: http://localhost:8000
echo   - API Docs:    http://localhost:8000/docs
echo   - pgAdmin:     http://localhost:5050 (admin@keiba.local / admin)
echo   - Flower:      http://localhost:5555
echo.
echo Logs are available in ./logs/
echo.
echo To stop all services, run: scripts\stop_system.bat
pause