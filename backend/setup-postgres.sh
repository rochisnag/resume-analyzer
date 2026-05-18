#!/bin/bash

# Resume Analyzer - PostgreSQL Setup Script (Linux/macOS)

echo "🗄️ Resume Analyzer - PostgreSQL Setup"
echo "===================================="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found"
    echo ""
    echo "📥 Installation Instructions:"
    echo "   macOS:   brew install postgresql@15"
    echo "   Ubuntu:  sudo apt-get install postgresql"
    echo "   RHEL:    sudo yum install postgresql-server"
    exit 1
fi

echo "✅ PostgreSQL found"

# Start PostgreSQL service
echo ""
echo "Starting PostgreSQL service..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    brew services start postgresql || echo "PostgreSQL may already be running"
else
    sudo systemctl start postgresql || echo "PostgreSQL may already be running"
fi

sleep 2

# Database configuration
DB_USER="resume_user"
DB_PASSWORD="resume_password"
DB_NAME="resume_analyzer_db"

echo ""
echo "Creating database and user..."
echo "Database: $DB_NAME"
echo "User: $DB_USER"

# Create database and user
psql -U postgres <<EOSQL
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

EOSQL

if [ $? -eq 0 ]; then
    echo "✅ Database setup completed successfully!"
    echo ""
    echo "📋 Database Details:"
    echo "   Host: localhost"
    echo "   Port: 5432"
    echo "   Database: $DB_NAME"
    echo "   User: $DB_USER"
    echo "   Password: $DB_PASSWORD"
else
    echo "❌ Failed to create database"
    exit 1
fi

echo ""
echo "✨ Setup complete! Next steps:"
echo "   1. Copy .env.example to .env"
echo "   2. Update .env with database credentials"
echo "   3. Run: pip install -r requirements.txt"
echo "   4. Run: python main.py"
