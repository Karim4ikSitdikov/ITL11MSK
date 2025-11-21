#!/bin/bash

echo "======================================"
echo "Stoloto Assistant - Quick Start"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
echo ""

# Check PostgreSQL
echo "Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL found"
    
    # Check if database exists
    psql -lqt | cut -d \| -f 1 | grep -qw stoloto_db
    if [ $? -ne 0 ]; then
        echo "  Creating database..."
        createdb stoloto_db
        echo "  ✓ Database created"
    else
        echo "  ✓ Database exists"
    fi
else
    echo "⚠ PostgreSQL not found"
    echo "  Install it with: brew install postgresql"
    echo "  Then start it with: brew services start postgresql"
fi
echo ""

# Initialize database schema
echo "Initializing database schema..."
python app.py --init-db
if [ $? -eq 0 ]; then
    echo "✓ Schema initialized"
else
    echo "⚠ Schema initialization had issues (may already exist)"
fi
echo ""

# Load data
echo "Loading lottery data..."
python parsers/db_loader.py --all
if [ $? -eq 0 ]; then
    echo "✓ Data loaded"
else
    echo "⚠ Data loading had issues"
fi
echo ""

# Check Ollama
echo "Checking Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Ollama is running"
    
    # Check if model exists
    if ollama list | grep -q "llama3.2"; then
        echo "  ✓ Model llama3.2 is available"
    else
        echo "  ⚠ Model llama3.2 not found"
        echo "  Pulling model (this may take a while)..."
        ollama pull llama3.2
    fi
else
    echo "⚠ Ollama is not running"
    echo "  Start it in another terminal with: ollama serve"
    echo "  Then pull the model with: ollama pull llama3.2"
fi
echo ""

# Run tests
echo "Running tests..."
python tests/test_suite.py
test_result=$?
echo ""

if [ $test_result -eq 0 ]; then
    echo "======================================"
    echo "✓ Setup Complete!"
    echo "======================================"
    echo ""
    echo "Start the application with:"
    echo "  python app.py"
    echo ""
    echo "Then open http://localhost:5000 in your browser"
    echo ""
else
    echo "======================================"
    echo "⚠ Setup Complete with Warnings"
    echo "======================================"
    echo ""
    echo "Some tests failed, but you can still try running:"
    echo "  python app.py"
    echo ""
fi
