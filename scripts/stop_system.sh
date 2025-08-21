#!/bin/bash

# Keiba Analysis System Stop Script

echo "======================================"
echo "  Stopping Keiba Analysis System"
echo "======================================"

# Kill Node.js processes (Frontend)
echo "Stopping frontend..."
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# Kill Python processes (Backend)
echo "Stopping backend API..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true

echo "Stopping Celery workers..."
pkill -f "celery.*worker" 2>/dev/null || true

echo "Stopping Celery beat..."
pkill -f "celery.*beat" 2>/dev/null || true

# Stop Docker services
echo "Stopping Docker services..."
docker-compose --profile tools --profile app --profile worker down

echo ""
echo "All services stopped."