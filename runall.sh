#!/bin/bash

# Base command
base_cmd="python temp.py"

# Directory pattern
dir_pattern="$1/*/*/"

# Find all matching directories and execute the Python script
for dir in $dir_pattern; do
    if [ -d "$dir" ]; then
        echo "Executing in directory: $dir"
        $base_cmd "$dir"
        echo "------------------------"
    fi
done