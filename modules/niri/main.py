import argparse
import subprocess
import sys
from pathlib import Path


def get_scripts_directory() -> Path:
    """Return the absolute directory containing this file."""
    return Path(__file__).resolve().parent


def build_command(script_filename: str, extra_args: list[str] | None = None) -> list[str]:
    """Build a command to execute a sibling script with the current Python.

    Args:
        script_filename: The name of the script file to run (e.g., "launch-music.py").
        extra_args: Additional CLI arguments to pass through to the script.

    Returns:
        A list suitable for subprocess execution.
    """
    script_path = get_scripts_directory() / script_filename
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def run_command(cmd: list[str]) -> int:
    """Run a command and return its exit code."""
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


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

    # Map subcommands to script filenames
    script_map: dict[str, str] = {
        "launch-music": "launch-music.py",
        "window-glancer": "window-glancer.py",
        "dynamic-float": "dynamic-float.py",
    }

    if args.command == "launch-music":
        return run_command(build_command(script_map["launch-music"]))

    if args.command == "window-glancer":
        passthrough = []
        if getattr(args, "glancer_cmd", None):
            passthrough = [args.glancer_cmd]
        return run_command(build_command(script_map["window-glancer"], passthrough))

    if args.command == "dynamic-float":
        # long-running; just exec and adopt its exit code when it ends
        return run_command(build_command(script_map["dynamic-float"]))

    # Should not reach here because subparser requires a command
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


