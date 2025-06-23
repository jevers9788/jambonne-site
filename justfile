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
    cd mindmap-service && uv pip install ruff && uv run ruff check . 