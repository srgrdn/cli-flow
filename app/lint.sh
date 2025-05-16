#!/bin/bash

# Run ruff linter on the codebase
echo "Running ruff linter..."
python -m ruff check .

# If the --fix flag is provided, run ruff with autofix
if [ "$1" == "--fix" ]; then
    echo "Attempting to fix issues..."
    python -m ruff check --fix .
    echo "Fixes applied!"
fi

# Summary
echo "Linting completed!" 