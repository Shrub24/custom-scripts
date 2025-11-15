#!/bin/bash
set -euo pipefail
# This script installs dependencies for the 'theme' module.

echo "  (theme) Setting up venv..."
pkg_dir=$(dirname "$(readlink -f "$0")") # This is the theme/ directory
repo_root="${1:-$pkg_dir/../..}" # Passed as arg or fallback
venv_dir="$pkg_dir/.venv"

# 1. Create venv
if [ ! -d "$venv_dir" ]; then
    (cd "$pkg_dir" && uv venv)
fi

# 2. Sync module dependencies
(cd "$pkg_dir" && uv sync)

# 3. Install helpers package in editable mode
(cd "$pkg_dir" && uv pip install -e "$repo_root")

echo "  (theme) Venv is up to date."
