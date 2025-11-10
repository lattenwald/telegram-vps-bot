#!/bin/bash
# Quick setup script for Telegram VPS Bot

set -e  # Exit on error

echo "🚀 Setting up Telegram VPS Bot..."

# Check if uv is installed
if command -v uv &> /dev/null; then
    echo "✓ Found uv - using fast installation"
    USE_UV=true
else
    echo "⚠ uv not found - using pip (slower)"
    echo "💡 Tip: Install uv for faster setup: curl -LsSf https://astral.sh/uv/install.sh | sh"
    USE_UV=false
fi

# Check Python version
PYTHON_CMD=""
if command -v python3.13 &> /dev/null; then
    PYTHON_CMD="python3.13"
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3.13"; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null && python3 --version 2>&1 | grep -q "Python 3.13"; then
    PYTHON_CMD="python3"
else
    echo "❌ Python 3.13 not found."
    echo ""
    echo "Please install Python 3.13 using one of these methods:"
    echo ""
    echo "  Option 1: Using asdf (recommended)"
    echo "    asdf plugin add python"
    echo "    asdf install python 3.13.1"
    echo "    asdf local python 3.13.1"
    echo ""
    echo "  Option 2: Using system package manager"
    echo "    sudo apt install python3.13  # Ubuntu/Debian"
    echo "    brew install python@3.13     # macOS"
    echo ""
    exit 1
fi

echo "✓ Found Python 3.13 at: $(which $PYTHON_CMD)"

# Create virtual environment
if [ "$USE_UV" = true ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv --python 3.13
else
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
if [ "$USE_UV" = true ]; then
    echo "📥 Installing dependencies with uv (fast!)..."
    uv pip install -r requirements.txt
    uv pip install -r requirements-dev.txt
else
    echo "📥 Installing dependencies with pip..."
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Configure AWS secrets (see docs/SETUP.md)"
echo ""
echo "  3. Run tests:"
echo "     pytest tests/ -v"
echo ""
echo "  4. Deploy to AWS:"
echo "     cd infrastructure && terraform init && terraform apply"
echo ""
