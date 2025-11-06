#!/bin/bash
set -euo pipefail

# The package name is the first argument (e.g., "niri")
PACKAGE_NAME=$1
shift # Remove the first argument, the rest are for python

# --- THIS IS THE KEY ---
# Find the script's own location, then find the packages
# This makes the script's location independent.
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# We assume this 'run' script lives in ~/.local/bin
# and the packages live in ~/Projects/my-script-pkgs
PKG_BASE_DIR="$HOME/Projects/my-script-pkgs"
PKG_DIR="$PKG_BASE_DIR/$PACKAGE_NAME"

# Look for .venv, which uv creates by default
VENV_DIR="$PKG_DIR/.venv" 
VENV_PYTHON="$VENV_DIR/bin/python"
PKG_MAIN_PY="$PKG_DIR/main.py"

# Check if the package and its venv exist
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Package '$PACKAGE_NAME' or its venv not found." >&2
    echo "Expected venv at: $VENV_DIR" >&2
    echo "Run '$HOME/Projects/my-script-pkgs/install.sh' to install." >&2
    exit 1
fi

# Execute the package's main.py with its venv and all remaining args
exec "$VENV_PYTHON" "$PKG_MAIN_PY" "$@"