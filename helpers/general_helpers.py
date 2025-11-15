"""
General helpers for script configuration (XDG) and logging.

Provides XDG-compliant directory management, logging setup, and configuration
loading for any script suite/module.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tomllib
from pathlib import Path
from typing import Any
from xdg import BaseDirectory


# Suite name for all scripts in this repository
SUITE_NAME = "custom-scripts"


class ScriptConfig:
    """Manages XDG-compliant configuration and state for scripts.

    This class is generic and can be used by any module within the repository.
    """

    def __init__(self, module_name: str, script_name: str, load_config: bool = True, module_dir: Path | None = None):
        if not isinstance(script_name, str) or not script_name.strip():
            raise ValueError("script_name must be a non-empty string")
        if not isinstance(module_name, str) or not module_name.strip():
            raise ValueError("module_name must be a non-empty string")

        self.module_name = module_name
        self.script_name = script_name
        self.module_dir = module_dir  # Optional: physical module directory

        # XDG-compliant directories
        self.config_dir = Path(BaseDirectory.save_config_path(SUITE_NAME)) / module_name
        self.state_dir = Path(BaseDirectory.save_state_path(SUITE_NAME)) / module_name

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Script-specific paths
        self.log_file = self.state_dir / f"{script_name}.log"
        self.config_file = self.config_dir / f"{script_name}.toml"
        self.state_file = self.state_dir / f"{script_name}_state"

        # Ensure files exist (create valid JSON for state)
        self.log_file.touch(exist_ok=True)
        if not self.state_file.exists():
            try:
                self.state_file.write_text("{}\n", encoding="utf-8")
            except OSError:
                # Best-effort; load_state will handle absence/invalid
                pass

        # Load configuration if available
        self.config: dict[str, Any] = {}
        if load_config:
            # Load general suite config from ~/.config/custom-scripts/config.toml (if exists)
            # Note: The shell config.sh is only for bash entrypoint, not Python
            general_config_path = Path(BaseDirectory.save_config_path(SUITE_NAME)) / "config.toml"
            if general_config_path.exists():
                with open(general_config_path, "rb") as f:
                    self.config = tomllib.load(f)
            
            # Load module-specific config and merge (module config takes precedence)
            if self.config_file.exists():
                with open(self.config_file, "rb") as f:
                    module_config = tomllib.load(f)
                    self.config.update(module_config)

    def get_config_value(self, key: str, default: Any | None = None) -> Any:
        """Return a possibly expanded configuration value or default."""
        return self.get_config_value_checked(key, default=default, require_str=False)

    def get_config_value_checked(
        self,
        key: str,
        default: Any | None = None,
        *,
        require_str: bool = False,
        allow_empty: bool = False,
    ) -> Any:
        value = self.config.get(key, default)

        if isinstance(value, str):
            value = os.path.expandvars(value)
            value = os.path.expanduser(value)

        if require_str:
            if value is None:
                raise ValueError(f"Configuration value for '{key}' is required and not set")
            if not isinstance(value, str):
                if isinstance(value, (int, float, bool)):
                    value = str(value)
                else:
                    raise ValueError(
                        f"Configuration value for '{key}' must be a string; got {type(value).__name__}"
                    )
            if not allow_empty and value.strip() == "":
                raise ValueError(f"Configuration value for '{key}' must not be empty")

        return value

    def setup_logging(self, level=logging.INFO, include_console=True):
        """Setup logging to file and optionally console."""
        handlers: list[logging.Handler] = [logging.FileHandler(self.log_file)]
        if include_console:
            handlers.append(logging.StreamHandler())

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers,
            force=True,
        )

        log = logging.getLogger(self.script_name)
        log.info("Logging initialized. Log file: %s", self.log_file)
        return log

    def load_state(self, default=None):
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default if default is not None else {}

    def save_state(self, state: dict):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (IOError, OSError) as e:
            logging.getLogger(self.script_name).error("Failed to save state: %s", e)

    def get_config_path(self, filename: str) -> Path:
        """Get a path to a config file in the module's config directory.
        
        Args:
            filename: Name of the config file
            
        Returns:
            Path to the config file (may not exist)
        """
        return self.config_dir / filename


