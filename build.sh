#!/bin/bash
set -e

# Build the Rust application
cargo build --release

# Ensure static files and posts are in the right place
echo "Build completed successfully!" 