#!/bin/bash

# Safari Reading List Mind Map Generator - Setup Script

echo "🚀 Setting up Safari Reading List Mind Map Generator..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    
    # Try to install uv
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "✅ uv installed successfully!"
    else
        echo "❌ curl not found. Please install uv manually:"
        echo "   pip install uv"
        exit 1
    fi
else
    echo "✅ uv is already installed"
fi

# Install dependencies from requirements.txt
if [ -f requirements.txt ]; then
    echo "📦 Installing dependencies from requirements.txt..."
    uv pip install -r requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "🎉 Setup complete! You can now run:"
    echo "   uv run python reading_list.py"
    echo "   uv run python mind_map_visualizer.py"
    echo ""
    echo "📖 See README.md for more information"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi 