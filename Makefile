# Makefile for Keiba Analysis Project

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker commands
.PHONY: docker-up
docker-up: ## Start Docker containers
	docker-compose up -d postgres redis

.PHONY: docker-down
docker-down: ## Stop Docker containers
	docker-compose down

.PHONY: docker-logs
docker-logs: ## Show Docker logs
	docker-compose logs -f

# Backend commands
.PHONY: backend-install
backend-install: ## Install backend dependencies
	cd backend && poetry install

.PHONY: backend-run
backend-run: ## Run backend server
	cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: backend-worker
backend-worker: ## Run Celery worker
	cd backend && poetry run celery -A app.tasks.celery_app worker --loglevel=info

.PHONY: backend-beat
backend-beat: ## Run Celery beat scheduler
	cd backend && poetry run celery -A app.tasks.celery_app beat --loglevel=info

.PHONY: backend-flower
backend-flower: ## Run Flower (Celery monitoring)
	cd backend && poetry run celery -A app.tasks.celery_app flower

# Database commands
.PHONY: db-migrate
db-migrate: ## Create database migration
	cd backend && poetry run alembic revision --autogenerate -m "$(msg)"

.PHONY: db-upgrade
db-upgrade: ## Apply database migrations
	cd backend && poetry run alembic upgrade head

.PHONY: db-downgrade
db-downgrade: ## Rollback database migration
	cd backend && poetry run alembic downgrade -1

.PHONY: db-reset
db-reset: ## Reset database (drop and recreate)
	cd backend && poetry run alembic downgrade base && poetry run alembic upgrade head

# Test commands
.PHONY: test
test: ## Run all tests
	cd backend && poetry run pytest

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	cd backend && poetry run pytest --cov=app --cov-report=html

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	cd backend && poetry run ptw

# Lint commands
.PHONY: lint
lint: ## Run linters
	cd backend && poetry run ruff check app tests
	cd backend && poetry run black --check app tests

.PHONY: format
format: ## Format code
	cd backend && poetry run black app tests
	cd backend && poetry run ruff check --fix app tests

.PHONY: type-check
type-check: ## Run type checking
	cd backend && poetry run mypy app

# Development shortcuts
.PHONY: dev
dev: docker-up ## Start development environment
	@echo "Starting development environment..."
	@echo "Waiting for services to be ready..."
	@sleep 5
	$(MAKE) db-upgrade
	$(MAKE) backend-run

.PHONY: dev-worker
dev-worker: ## Start development worker
	$(MAKE) backend-worker

.PHONY: dev-full
dev-full: docker-up ## Start full development environment (API + Worker + Scheduler)
	@echo "Starting full development environment..."
	@echo "Run the following commands in separate terminals:"
	@echo "1. make backend-run"
	@echo "2. make backend-worker"
	@echo "3. make backend-beat"
	@echo "4. make backend-flower (optional)"

# Scraping commands
.PHONY: scrape-today
scrape-today: ## Scrape today's races
	@curl -X POST http://localhost:8000/api/scraping/start \
		-H "Content-Type: application/json" \
		-d '{"start_date": "$(shell date +%Y-%m-%d)", "end_date": "$(shell date +%Y-%m-%d)"}'

.PHONY: scrape-status
scrape-status: ## Check scraping status
	@curl http://localhost:8000/api/scraping/status | python -m json.tool

# Clean commands
.PHONY: clean
clean: ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf backend/htmlcov
	rm -rf backend/.pytest_cache

.PHONY: clean-all
clean-all: clean docker-down ## Clean everything including Docker volumes
	docker-compose down -v