#!/bin/bash
set -euo pipefail
# This script installs scripts from the 'chezmoi' module.

MODULE_ROOT=$(dirname "$(readlink -f "$0")")
DEST_BIN_DIR="$HOME/.local/bin"

echo "  -> Installing 'chezmoi-sym' plugin..."
cp "$MODULE_ROOT/sym" "$DEST_BIN_DIR/chezmoi-sym"
chmod +x "$DEST_BIN_DIR/chezmoi-sym"
echo "  -> chezmoi-sym installed successfully."