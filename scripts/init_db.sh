#!/bin/bash

echo "======================================"
echo "Stoloto Assistant - Database Setup"
echo "======================================"
echo ""

# Check if PostgreSQL is running
if ! command -v psql &> /dev/null
then
    echo "❌ PostgreSQL is not installed or not in PATH"
    echo "Please install PostgreSQL first: brew install postgresql"
    exit 1
fi

echo "✓ PostgreSQL found"
echo ""

# Database configuration
DB_NAME=${DB_NAME:-"stoloto_db"}
DB_USER=${DB_USER:-$(whoami)}

echo "Creating database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Create database
createdb $DB_NAME 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Database created successfully"
else
    echo "⚠ Database may already exist, continuing..."
fi

echo ""
echo "Initializing schema..."

# Initialize schema using Python
python3 app.py --init-db

if [ $? -eq 0 ]; then
    echo "✓ Schema initialized successfully"
else
    echo "❌ Failed to initialize schema"
    exit 1
fi

echo ""
echo "======================================"
echo "Database setup complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Load lottery data: python parsers/db_loader.py --all"
echo "2. Start the app: python app.py"
echo ""
