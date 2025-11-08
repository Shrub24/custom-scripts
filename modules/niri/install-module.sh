#!/bin/bash
set -euo pipefail
# This script installs dependencies for the 'niri' module.

echo "  (niri) Setting up venv..."
pkg_dir=$(dirname "$(readlink -f "$0")") # This is the niri/ directory
venv_dir="$pkg_dir/.venv"

# 1. Create venv
if [ ! -d "$venv_dir" ]; then
    (cd "$pkg_dir" && uv venv)
fi

# 2. Sync dependencies
(cd "$pkg_dir" && uv sync)
echo "  (niri) Venv is up to date."