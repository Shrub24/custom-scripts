"""
Common helper functions for niri scripts.

Provides XDG-compliant directory management, logging setup, and configuration loading.
"""

import json
import logging
import os
import tomllib
from pathlib import Path
from socket import AF_UNIX, socket
from xdg import BaseDirectory
from typing import Any, Optional

# Suite name for all niri scripts
SUITE_NAME = "custom-scripts"


class NiriScriptConfig:
    """Manages XDG-compliant configuration and state for niri scripts."""

    def __init__(self, module_name: str, script_name: str, load_config: bool = True):
        """
        Initialize script configuration.

        Args:
            script_name: Name of the script (e.g., "launch-music", "hp-layout-switcher")
            load_config: Whether to load config.toml file
        """
        # Validate script_name: must be a non-empty string
        if not isinstance(script_name, str) or not script_name.strip():
            raise ValueError("script_name must be a non-empty string")
        if not isinstance(module_name, str) or not module_name.strip():
            raise ValueError("module_name must be a non-empty string")
        
        self.module_name = module_name
        self.script_name = script_name

        # Setup XDG-compliant directories
        # BaseDirectory functions may return paths with ~ that need expansion
        self.config_dir = Path(BaseDirectory.save_config_path(SUITE_NAME)) / module_name
        self.state_dir = Path(BaseDirectory.save_state_path(SUITE_NAME)) / module_name

        # Script-specific paths
        self.log_file = self.state_dir / f"{script_name}.log"
        self.config_file = self.config_dir / f"{script_name}.toml"
        self.state_file = self.state_dir / f"{script_name}_state"

        # Load configuration if requested
        self.config = {}
        if load_config and self.config_file.exists():
            with open(self.config_file, "rb") as f:
                self.config = tomllib.load(f)

    def get_config_value(self, key: str, default=None):
        """
        Get a configuration value with environment variable expansion.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value with environment variables expanded
        """
        return self.get_config_value_checked(key, default=default, require_str=False)

    def get_config_value_checked(self, key: str, default: Any = None, *, require_str: bool = False, allow_empty: bool = False) -> Any:
        """
        Get a configuration value with environment variable expansion and optional validation.

        Args:
            key: Configuration key
            default: Default value if key not found
            require_str: If True, guarantee a string is returned; raise ValueError otherwise.
            allow_empty: If False and require_str is True, an empty string will raise ValueError.

        Returns:
            Configuration value (possibly expanded) or default.
        """
        value = self.config.get(key, default)

        # Expand environment variables for strings
        if isinstance(value, str):
            value = os.path.expandvars(value)
            value = os.path.expanduser(value)

        # If caller requires a string, enforce it
        if require_str:
            if value is None:
                # No default provided and key missing
                raise ValueError(f"Configuration value for '{key}' is required and not set")
            if not isinstance(value, str):
                # Try to coerce to string, but only if it's a simple scalar
                if isinstance(value, (int, float, bool)):
                    value = str(value)
                else:
                    raise ValueError(f"Configuration value for '{key}' must be a string; got {type(value).__name__}")
            if not allow_empty and value.strip() == "":
                raise ValueError(f"Configuration value for '{key}' must not be empty")

        return value

    def setup_logging(self, level=logging.INFO, include_console=True):
        """
        Setup logging to file and optionally console.

        Args:
            level: Logging level (default: INFO)
            include_console: Whether to also log to console

        Returns:
            Configured logger instance
        """
        handlers = [logging.FileHandler(self.log_file)]
        if include_console:
            handlers.append(logging.StreamHandler())

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers,
            force=True  # Override any existing config
        )

        log = logging.getLogger(self.script_name)
        log.info(f"Logging initialized. Log file: {self.log_file}")

        return log

    def load_state(self, default=None):
        """
        Load state from JSON state file.
        
        Args:
            default: Default value if state file doesn't exist
            
        Returns:
            Loaded state dictionary or default value
        """
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.debug("Could not load state: %s", e)
            return default if default is not None else {}
    
    def save_state(self, state: dict):
        """
        Save state to JSON state file.

        Args:
            state: Dictionary to save as state
        """
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (IOError, OSError) as e:
            logging.error("Failed to save state: %s", e)


class NiriIPC:
    """Helper class for Niri IPC communication."""

    def __init__(self):
        """Initialize Niri IPC helper."""
        if "NIRI_SOCKET" not in os.environ:
            raise RuntimeError("NIRI_SOCKET environment variable not set")
        self.socket_path = os.environ["NIRI_SOCKET"]
        self.log = logging.getLogger("NiriIPC")

    def send_request(self, request_name: str, *, require_str: bool = True) -> Optional[Any]:
        """
        Send a request to Niri IPC and return the parsed response.

        Args:
            request_name: Name of the request (e.g., "Windows", "Workspaces")

        Returns:
            Parsed response data or None on error
        """
        # Validate request_name
        if require_str:
            if not isinstance(request_name, str) or not request_name.strip():
                raise ValueError("request_name must be a non-empty string")

        json_str = json.dumps(request_name)
        self.log.debug("Sending request: %s", json_str)

        try:
            with socket(AF_UNIX) as s:
                s.settimeout(0.5)
                s.connect(self.socket_path)
                s.sendall((json_str + "\n").encode())
                response = s.recv(8192).decode()
                self.log.debug("Response: %s", response.strip())

                parsed = json.loads(response)

                # Niri returns {"Ok": {<RequestName>: <data>}} or {"Err": <error>}
                if "Ok" in parsed:
                    ok_data = parsed["Ok"]
                    if isinstance(ok_data, dict) and request_name in ok_data:
                        return ok_data[request_name]
                    else:
                        return ok_data
                else:
                    self.log.error("Request error: %s", parsed.get('Err'))
                    return None
        except (OSError, json.JSONDecodeError, KeyError) as e:
            self.log.error("Failed to send request: %s", e)
            return None

    def send_action(self, action: dict):
        """
        Send an action to Niri IPC.

        Args:
            action: Action dictionary (e.g., {"FocusWindow": {"id": 123}})
        """
        # Validate action
        if not isinstance(action, dict) or not action:
            raise ValueError("action must be a non-empty dict")

        # Convert Python True/False to lowercase true/false for Niri
        json_str = json.dumps({"Action": action})
        json_str = json_str.replace(': True', ': true').replace(': False', ': false')

        self.log.debug("Sending action: %s", json_str)

        try:
            with socket(AF_UNIX) as s:
                s.settimeout(0.5)
                s.connect(self.socket_path)
                s.sendall((json_str + "\n").encode())
                response = s.recv(8192).decode()
                self.log.debug("Response: %s", response.strip())
        except (OSError, ConnectionError) as e:
            self.log.error("Failed to send action: %s", e)
