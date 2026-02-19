# ListenBrainz Development Environment Setup Script
# This script sets up the ListenBrainz development environment

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "ListenBrainz Development Setup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Navigate to docker directory
$dockerDir = Join-Path $PSScriptRoot "docker"
Set-Location $dockerDir

# Build Docker images
Write-Host ""
Write-Host "Building Docker images (this may take several minutes)..." -ForegroundColor Yellow
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to build Docker images" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker images built successfully" -ForegroundColor Green

# Start services
Write-Host ""
Write-Host "Starting Docker Compose services..." -ForegroundColor Yellow
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Services started" -ForegroundColor Green

# Wait for services to be ready
Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Initialize databases
Write-Host ""
Write-Host "Initializing databases..." -ForegroundColor Yellow
docker compose exec -T web python3 manage.py init_db --create-db
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to initialize PostgreSQL database" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] PostgreSQL database initialized" -ForegroundColor Green

docker compose exec -T web python3 manage.py init_ts_db --create-db
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to initialize TimescaleDB database" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] TimescaleDB database initialized" -ForegroundColor Green

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are running:" -ForegroundColor Yellow
Write-Host "  - Web server: http://localhost:8100" -ForegroundColor White
Write-Host "  - API Compat: http://localhost:8101" -ForegroundColor White
Write-Host "  - WebSockets: ws://localhost:8102" -ForegroundColor White
Write-Host "  - RabbitMQ Management: http://localhost:25672" -ForegroundColor White
Write-Host "  - CouchDB: http://localhost:5984" -ForegroundColor White
Write-Host ""
Write-Host 'To stop services: docker compose -f docker/docker-compose.yml down' -ForegroundColor Gray
Write-Host 'To view logs: docker compose -f docker/docker-compose.yml logs -f' -ForegroundColor Gray
Write-Host ""
