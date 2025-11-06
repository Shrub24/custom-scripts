#!/bin/bash
set -euo pipefail
# This script installs all packages and entrypoints from this repo.

# Get the directory this script is in (the repo root)
REPO_ROOT=$(dirname "$(readlink -f "$0")")

# --- 1. Install/Update Virtual Environments ---
echo "Updating Python virtual environments using uv..."
find "$REPO_ROOT" -name "pyproject.toml" -print0 | while IFS= read -r -d '' config_file; do
    pkg_dir=$(dirname "$config_file")
    venv_dir="$pkg_dir/.venv"
    echo "Checking package: $(basename "$pkg_dir")"

    if [ ! -d "$venv_dir" ]; then
        echo "  -> Creating .venv with 'uv venv'..."
        (cd "$pkg_dir" && uv venv)
    fi
    echo "  -> Syncing dependencies with 'uv sync'..."
    (cd "$pkg_dir" && uv sync)
done
echo "Python venvs are up to date."

# --- 2. Install/Update the 'run' Entrypoint ---
echo "Installing 'run' entrypoint to ~/.local/bin..."
DEST_BIN_DIR="$HOME/.local/bin"
DEST_RUN_SCRIPT="$DEST_BIN_DIR/run"
SOURCE_RUN_SCRIPT="$REPO_ROOT/run"

# Ensure ~/.local/bin exists
mkdir -p "$DEST_BIN_DIR"

# Copy the file and make it executable
cp "$SOURCE_RUN_SCRIPT" "$DEST_RUN_SCRIPT"
chmod +x "$DEST_RUN_SCRIPT"

echo "Installation complete. '$DEST_RUN_SCRIPT' is ready."