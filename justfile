# Rust project shortcuts using Just
# Usage: just <command>

# Build the project
build:
    cargo build

style:
    ./scripts/style.sh
# Build in release mode
release:
    cargo build --release

# Clean build artifacts
clean:
    cargo clean

# Run the project
run:
    cargo run

# Run in development mode
dev:
    cargo run

# Check for errors without building
check:
    cargo check

# Format code
fmt:
    cargo fmt

# Run clippy linter
clippy:
    cargo clippy

# Run all checks (format + clippy)
lint: fmt clippy

# Quick build and run
br: build run

# Clean and rebuild
rebuild: clean build

# Show available commands
default:
    @just --list

lint-all:
    just lint
    cd scripts && uv pip install ruff && uv run ruff check .
    @echo "Skipping mindmap-service lint (service currently decoupled)."

# Optional helper while the mindmap service evolves separately
lint-mindmap:
    cd mindmap-service && uv pip install ruff && uv run ruff check . 

# Export Safari reading list to JSON file used by the Rust app
export-reading-list:
    uv run python scripts/export_reading_list.py --output static/data/reading_list.json
