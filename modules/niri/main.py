import argparse
import sys
from pathlib import Path

from helpers import get_module_directory


def get_scripts_directory() -> Path:
    """Return the absolute directory containing this file."""
    return get_module_directory(__file__)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="niri",
        description="Entrypoint for niri helper scripts.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # launch-music
    subparsers.add_parser(
        "launch-music",
        help="Launch or focus the configured music apps and arrange them.",
    )

    # window-glancer
    parser_glancer = subparsers.add_parser(
        "window-glancer",
        help="Toggle a window between primary and glance layouts.",
    )
    parser_glancer.add_argument(
        "glancer_cmd",
        nargs="?",
        choices=["primary", "glance", "toggle"],
        default=None,
        help="Optional action to run (defaults to 'toggle').",
    )

    # dynamic-float
    subparsers.add_parser(
        "dynamic-float",
        help="Float windows dynamically based on rules in dynamic-float.toml.",
    )

    return parser


def main(argv: list[str]) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    # Import the actual script modules and call their main functions
    # This works because we're running as a package with python -m
    
    if args.command == "launch-music":
        from . import launch_music
        return launch_music.main()
    
    if args.command == "window-glancer":
        from . import window_glancer
        glancer_args = []
        if getattr(args, "glancer_cmd", None):
            glancer_args = [args.glancer_cmd]
        return window_glancer.main(glancer_args)
    
    if args.command == "dynamic-float":
        from . import dynamic_float
        return dynamic_float.main()

    # Should not reach here because subparser requires a command
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


