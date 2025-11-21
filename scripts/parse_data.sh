#!/bin/bash

echo "======================================"
echo "Stoloto Assistant - Data Loader"
echo "======================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: Virtual environment not activated"
    echo "Activate it with: source venv/bin/activate"
    echo ""
fi

# Check if Ollama is running
echo "Checking Ollama..."
curl -s http://localhost:11434/api/tags > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Ollama is running"
else
    echo "⚠ Ollama is not running"
    echo "Start it with: ollama serve (in another terminal)"
    echo ""
fi

echo ""
echo "Loading lottery data..."
echo ""

python3 parsers/db_loader.py --all

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "Data loading complete!"
    echo "======================================"
    echo ""
    echo "You can now start the application:"
    echo "  python app.py"
    echo ""
else
    echo ""
    echo "❌ Data loading failed"
    exit 1
fi
