#!/bin/bash

# Keiba Analysis System Startup Script

set -e

echo "======================================"
echo "  Keiba Analysis System Startup"
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration and run this script again."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Function to check if service is ready
check_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0

    echo -n "Waiting for $service..."
    
    while ! nc -z localhost $port 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            echo " Failed!"
            echo "Error: $service did not start within expected time."
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo " Ready!"
}

# Start Docker services
echo ""
echo "Starting Docker services..."
docker-compose up -d postgres redis

# Wait for PostgreSQL
check_service "PostgreSQL" 5432

# Wait for Redis
check_service "Redis" 6379

# Run database migrations
echo ""
echo "Running database migrations..."
cd backend
poetry run alembic upgrade head
cd ..

# Start backend services in background
echo ""
echo "Starting backend services..."

# Start API server
cd backend
nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/api.log 2>&1 &
echo "API server started (PID: $!)"
cd ..

# Wait for API
check_service "API" 8000

# Start Celery worker
cd backend
nohup poetry run celery -A app.core.celery_app worker --loglevel=info > ../logs/celery-worker.log 2>&1 &
echo "Celery worker started (PID: $!)"

# Start Celery beat
nohup poetry run celery -A app.core.celery_app beat --loglevel=info > ../logs/celery-beat.log 2>&1 &
echo "Celery beat started (PID: $!)"
cd ..

# Start frontend
echo ""
echo "Starting frontend..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
echo "Frontend started (PID: $!)"
cd ..

# Wait for frontend
check_service "Frontend" 3000

# Optional: Start monitoring tools
read -p "Start monitoring tools (pgAdmin, Flower)? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose --profile tools up -d
    echo "Monitoring tools started"
fi

echo ""
echo "======================================"
echo "  System Started Successfully!"
echo "======================================"
echo ""
echo "Services available at:"
echo "  - Frontend:    http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs:    http://localhost:8000/docs"
echo "  - pgAdmin:     http://localhost:5050"
echo "  - Flower:      http://localhost:5555"
echo ""
echo "Logs are available in ./logs/"
echo ""
echo "To stop all services, run: ./scripts/stop_system.sh"