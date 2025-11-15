#!/usr/bin/env python3
"""Theme module main entry point - routes hook events and commands."""

import argparse
import sys
from pathlib import Path

from .wallpaper_changed import wallpaper_changed


def main() -> int:
    """Main entry point for theme module."""
    parser = argparse.ArgumentParser(
        description="Theme module - handle theme-related hooks and operations"
    )
    parser.add_argument(
        "command",
        help="Command or hook to execute (onWallpaperChanged, wallpaper-changed)",
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Arguments for the command",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    # Handle hooks (called from hooks module)
    if args.command == "onWallpaperChanged":
        if len(args.args) < 1:
            print("Error: onWallpaperChanged requires wallpaper path", file=sys.stderr)
            return 1
        try:
            wallpaper_path = Path(args.args[0])
            wallpaper_changed(wallpaper_path, args.verbose)
            return 0
        except Exception as e:
            print(f"Error processing wallpaper: {e}", file=sys.stderr)
            return 1
    
    # Handle direct commands (for backwards compatibility)
    elif args.command == "wallpaper-changed":
        if len(args.args) < 1:
            print("Error: wallpaper-changed requires wallpaper path", file=sys.stderr)
            return 1
        try:
            wallpaper_path = Path(args.args[0])
            wallpaper_changed(wallpaper_path, args.verbose)
            return 0
        except Exception as e:
            print(f"Error processing wallpaper: {e}", file=sys.stderr)
            return 1
    
    else:
        print(f"Error: Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
