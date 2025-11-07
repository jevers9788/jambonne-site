.PHONY: setup install run-scrape clean format lint test help

# Default target
help:
	@echo "Safari Reading List Scripts"
	@echo "======================================"
	@echo ""
	@echo "Available commands:"
	@echo "  setup        - Install uv and dependencies"
	@echo "  install      - Install dependencies only"
	@echo "  run-scrape   - Run the reading list scraper"
	@echo "  clean        - Remove generated files"
	@echo "  format       - Format code with ruff"
	@echo "  lint         - Lint code with ruff"
	@echo "  test         - Run tests (if available)"
	@echo "  help         - Show this help message"
	@echo ""
	@echo "  (Ruff is now used for both linting and formatting. Install with: uv pip install ruff)"

# Setup the project
setup:
	@echo "🚀 Setting up Safari Reading List Mind Map Generator..."
	@./setup.sh

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	uv pip install -r requirements.txt

# Run the scraper
run-scrape:
	@echo "🔍 Running Safari reading list scraper..."
	uv run python reading_list.py

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	rm -f reading_list_content.json
	rm -f mind_map_data.json
	rm -f mind_map.png
	rm -f enhanced_mind_map.png
	rm -f mind_map_summary.txt
	@echo "✅ Cleaned!"

# Format code
format:
	@echo "🎨 Formatting code with ruff..."
	uv run ruff format .

# Lint code
lint:
	@echo "🔍 Linting code with ruff..."
	uv run ruff check .

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest

# Quick start - run scraper
all: run-scrape 