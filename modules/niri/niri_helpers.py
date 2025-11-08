"""
Common helper functions for niri scripts.

This file reuses the generic helpers in `helpers/general_helpers.py` for
config and logging, and keeps niri-specific IPC utilities here.
"""

import json
import logging
import os
from socket import AF_UNIX, socket
from typing import Any, Optional

try:
    # Prefer local helpers path when run inside this repository
    from helpers.general_helpers import ScriptConfig as NiriScriptConfig
except ImportError:  # pragma: no cover - fallback: add repo root to sys.path
    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from helpers.general_helpers import ScriptConfig as NiriScriptConfig  # type: ignore

__all__ = ["NiriScriptConfig", "NiriIPC"]

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
        except OSError as e:
            self.log.error("Failed to send action: %s", e)


