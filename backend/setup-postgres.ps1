# Resume Analyzer - PostgreSQL Setup Script (Windows PowerShell)

Write-Host "🗄️ Resume Analyzer - PostgreSQL Setup (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if PostgreSQL is installed
$postgresPath = Get-Command psql -ErrorAction SilentlyContinue
if ($postgresPath) {
    Write-Host "✅ PostgreSQL found" -ForegroundColor Green
} else {
    Write-Host "❌ PostgreSQL not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "📥 Installation Instructions:" -ForegroundColor Yellow
    Write-Host "   1. Download: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "   2. Run installer with default settings" -ForegroundColor Yellow
    Write-Host "   3. Remember the superuser password (default: postgres)" -ForegroundColor Yellow
    exit 1
}

# Start PostgreSQL service
Write-Host ""
Write-Host "Starting PostgreSQL service..." -ForegroundColor Cyan
$serviceNames = @("postgresql-x64-15", "PostgreSQL", "postgresql-x64-14", "postgresql-x64-13")

foreach ($serviceName in $serviceNames) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -ne "Running") {
            Start-Service -Name $serviceName -ErrorAction SilentlyContinue
            Write-Host "✅ Started service: $serviceName" -ForegroundColor Green
        } else {
            Write-Host "✅ Service already running: $serviceName" -ForegroundColor Green
        }
        break
    }
}

# Database configuration
$DB_USER = "resume_user"
$DB_PASSWORD = "resume_password"
$DB_NAME = "resume_analyzer_db"

Write-Host ""
Write-Host "Creating database and user..." -ForegroundColor Cyan
Write-Host "Database: $DB_NAME" -ForegroundColor White
Write-Host "User: $DB_USER" -ForegroundColor White

# Create SQL script
$sqlScript = @"
-- Create user
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Configure user
ALTER ROLE $DB_USER SET client_encoding TO 'utf8';
ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';
ALTER ROLE $DB_USER SET timezone TO 'UTC';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
"@

# Save to temporary file
$tempFile = "$env:TEMP\resume_analyzer_init.sql"
$sqlScript | Out-File -FilePath $tempFile -Encoding UTF8

# Execute
try {
    $env:PGPASSWORD = "postgres"  # Default PostgreSQL password
    & psql -U postgres -h localhost -f $tempFile
    Remove-Item $tempFile
    
    Write-Host ""
    Write-Host "✅ Database setup completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Database Details:" -ForegroundColor Cyan
    Write-Host "   Host: localhost" -ForegroundColor White
    Write-Host "   Port: 5432" -ForegroundColor White
    Write-Host "   Database: $DB_NAME" -ForegroundColor White
    Write-Host "   User: $DB_USER" -ForegroundColor White
    Write-Host "   Password: $DB_PASSWORD" -ForegroundColor White
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    if (Test-Path $tempFile) {
        Remove-Item $tempFile
    }
    exit 1
}

Write-Host ""
Write-Host "✨ Setup complete! Next steps:" -ForegroundColor Yellow
Write-Host "   1. Copy .env.example to .env" -ForegroundColor Yellow
Write-Host "   2. Update .env with database credentials" -ForegroundColor Yellow
Write-Host "   3. Run: pip install -r requirements.txt" -ForegroundColor Yellow
Write-Host "   4. Run: python main.py" -ForegroundColor Yellow
