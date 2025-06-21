#!/bin/bash
#
# A helper script to format and lint the Rust code.
#
# -e: Exit immediately if a command exits with a non-zero status.
set -e

echo "🎨 Formatting Rust code..."
cargo fmt

echo "🔍 Linting with Clippy..."
# We use -D warnings to treat all warnings as errors.
cargo clippy -- -D warnings

echo -e "\033[32mAll checks passed!\033[0m"