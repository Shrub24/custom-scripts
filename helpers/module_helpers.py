#!/usr/bin/env python3
"""Common utilities for module scripts."""

import argparse
import subprocess
import sys
from pathlib import Path


def get_module_directory(module_file: str) -> Path:
    """Get the directory of the calling module.
    
    Args:
        module_file: Should be __file__ from the calling module
        
    Returns:
        Path to the module directory
    """
    return Path(module_file).resolve().parent


def build_script_command(
    module_dir: Path, 
    script_filename: str, 
    extra_args: list[str] | None = None
) -> tuple[list[str], dict | None]:
    """Build a command to execute a script with the current Python.

    Args:
        module_dir: Directory containing the script
        script_filename: The name of the script file to run
        extra_args: Additional CLI arguments to pass through to the script

    Returns:
        A tuple of (command_list, env_dict) suitable for subprocess execution
        
    Raises:
        FileNotFoundError: If script doesn't exist
    """
    script_path = module_dir / script_filename
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    # Get module name and script name without extension
    module_name = module_dir.name
    script_name = script_filename.replace('.py', '')
    
    # Check if this is a package (has __init__.py)
    if (module_dir / "__init__.py").exists():
        # Run as a module to enable relative imports
        cmd = [sys.executable, "-m", f"{module_name}.{script_name}"]
    else:
        # Run as a script
        cmd = [sys.executable, str(script_path)]
    
    if extra_args:
        cmd.extend(extra_args)
    
    return cmd, None


def run_command(cmd: list[str], env: dict | None = None) -> int:
    """Run a command and return its exit code.
    
    Args:
        cmd: Command list to execute
        env: Optional environment variables
        
    Returns:
        Exit code from the command
    """
    completed = subprocess.run(cmd, check=False, env=env)
    return completed.returncode


def create_module_parser(
    prog: str,
    description: str,
    subcommands: dict[str, dict]
) -> argparse.ArgumentParser:
    """Create a standardized argument parser for a module.
    
    Args:
        prog: Program name
        description: Module description
        subcommands: Dictionary mapping command names to their config:
            - 'help': Help text for the subcommand
            - 'arguments': Optional list of argument configs as tuples:
                (args, kwargs) where args are positional arguments to add_argument
                and kwargs are keyword arguments
                
    Example:
        parser = create_module_parser(
            "theme",
            "Theme management utilities",
            {
                "wallpaper-changed": {
                    "help": "Process wallpaper change",
                    "arguments": [
                        (["wallpaper"], {"help": "Path to wallpaper"}),
                        (["-v", "--verbose"], {"action": "store_true", "help": "Verbose output"}),
                    ]
                }
            }
        )
        
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(prog=prog, description=description)
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    for cmd_name, cmd_config in subcommands.items():
        subparser = subparsers.add_parser(cmd_name, help=cmd_config.get("help", ""))
        
        # Add arguments if specified
        for args, kwargs in cmd_config.get("arguments", []):
            subparser.add_argument(*args, **kwargs)
    
    return parser
