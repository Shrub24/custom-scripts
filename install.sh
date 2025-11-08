#!/bin/bash
set -euo pipefail
# This script installs all packages, entrypoints, and config from this repo.

# Get the directory this script is in (the repo root)
REPO_ROOT=$(dirname "$(readlink -f "$0")")

# --- 1. Write the Configuration File ---
echo "Writing config file..."
# Use the XDG standard, default to ~/.config/run-custom
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/custom-scripts"
CONFIG_FILE="$CONFIG_DIR/config.toml"

# Ensure the config directory exists
mkdir -p "$CONFIG_DIR"

# Write the path of the repo to the config file
# This will overwrite any old path
echo "PKG_BASE_DIR=$REPO_ROOT" > "$CONFIG_FILE"
echo "Config written to $CONFIG_FILE"

# --- 2. Install/Update the 'run-custom' Entrypoint ---
echo "Installing 'run-custom' entrypoint to ~/.local/bin..."
DEST_BIN_DIR="$HOME/.local/bin"
DEST_SCRIPT="$DEST_BIN_DIR/run-custom"
SOURCE_SCRIPT="$REPO_ROOT/entrypoint"

mkdir -p "$DEST_BIN_DIR"
cp -f "$SOURCE_SCRIPT" "$DEST_SCRIPT"
chmod +x "$DEST_SCRIPT"

echo "Entrypoint installed to '$DEST_SCRIPT'."

# --- 3. Call install.sh in Each Submodule ---
echo "Running install.sh scripts in submodules..."

MODULES_DIR="$REPO_ROOT/modules"
if [ ! -d "$MODULES_DIR" ]; then
    echo "No modules directory found at $MODULES_DIR" >&2
    echo "Create $MODULES_DIR and place your modules inside it." >&2
    exit 1
fi

# Find and execute install.sh in each submodule
for module_dir in "$MODULES_DIR"/*; do
    if [ -d "$module_dir" ]; then
        module_name=$(basename "$module_dir")
        install_script="$module_dir/install-module.sh"
        
        if [ -f "$install_script" ]; then
            echo "Installing module: $module_name"
            chmod +x "$install_script"
            (cd "$module_dir" && ./install-module.sh)
        else
            echo "Skipping module '$module_name' (no install.sh found)"
        fi
    fi
done

echo "Installation complete. All modules installed."