#!/bin/bash

set -e

# 1. Clear the posts directory
rm -rf ./posts/*

# 2. Find all markdown files under ~/Desktop/writing (recursively)
find ~/Desktop/writing -type f -name '*.md' | while read -r file; do
    # 3. Extract the date from the file (expects 'DATE: <YY-MM-DD>' on a line)
    date=$(grep -m1 '^DATE: ' "$file" | awk '{print $2}')
    if [[ -z "$date" ]]; then
        echo "Skipping $file: no DATE line found"
        continue
    fi
    # 4. Get the original filename
    base=$(basename "$file")
    # 5. Copy to posts/ with new name
    cp "$file" "./posts/${date}-${base}"
done
