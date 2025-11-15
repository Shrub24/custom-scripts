#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#   "pyxdg == 0.28"
# ]
# ///
"""Toggle a window between primary and secondary (glance) layouts via hotkey."""

import re
import sys
from .niri_helpers import NiriScriptConfig, NiriIPC

# Initialize script configuration
script_config = NiriScriptConfig("niri", "window-glancer", load_config=True)
log = script_config.setup_logging(level="DEBUG")
niri = NiriIPC()

# Load configuration from config.toml
WINDOW_TITLE_REGEX = script_config.get_config_value("window_title_regex")
GLANCE_WORKSPACE_NAME = script_config.get_config_value("glance_workspace_name")
PRIMARY_MONITOR_NAME = script_config.get_config_value("primary_monitor")
SECONDARY_MONITOR_NAME = script_config.get_config_value("secondary_monitor")
PRIMARY_WORKSPACE = script_config.get_config_value("primary_workspace")

def get_workspace_info(monitor_name):
    """Get workspace information for a specific monitor."""
    workspaces = niri.send_request("Workspaces")
    active_window_id = None
    workspace_indices = []
    is_focused = False
    
    for ws in workspaces:
        # Get output name
        ws_output = ws.get("output")
        if isinstance(ws_output, dict):
            ws_output = ws_output.get("name")
        
        if ws_output == monitor_name:
            ws_idx = ws.get("idx", 0)
            workspace_indices.append(ws_idx)
            
            if ws.get("is_focused"):
                is_focused = True
            if ws.get("is_active"):
                active_window_id = ws.get("active_window_id")
    
    workspace_indices.sort()
    last_idx = workspace_indices[-1] if workspace_indices else 0

    return {
        'active_window_id': active_window_id,
        'last_workspace_idx': last_idx,
        "focused": is_focused
    }

def find_target_window():
    """Find the target window and return its details."""
    windows = niri.send_request("Windows") or []
    for win in windows:
        if re.search(WINDOW_TITLE_REGEX, win.get("title", ""), re.IGNORECASE):
            layout = win.get("layout", {})
            pos = layout.get("pos_in_scrolling_layout")
            column_index = pos[0] if pos and len(pos) >= 2 else None
            window_size = layout.get("window_size")
            width = window_size[0] if window_size and len(window_size) >= 2 else None
            log.info("Found window: id=%s, column=%s, width=%s", win['id'], column_index, width)
            return win["id"], column_index, width
    log.warning("Target window not found")
    return None, None, None

def get_current_state():
    state_data = script_config.load_state()
    state = state_data.get("state", "primary")
    saved_column = state_data.get("saved_column")
    saved_width = state_data.get("saved_width")
    saved_secondary_window_id = state_data.get("saved_secondary_window_id")
    
    log.info("Current state: %s, column: %s, width: %s, secondary_ws: %s", state, saved_column, saved_width, saved_secondary_window_id)
    return state, saved_column, saved_width, saved_secondary_window_id

def save_state(state, saved_column=None, saved_width=None, saved_secondary_window_id=None):
    data = {
        "state": state,
        "saved_column": saved_column,
        "saved_width": saved_width,
        "saved_secondary_window_id": saved_secondary_window_id
    }
    script_config.save_state(data)
    log.info("Saved state: %s", data)

def move_to_primary():
    log.info("=== Moving to primary layout ===")
    window_id, _, _ = find_target_window()
    if not window_id:
        log.error("Cannot move to primary: window not found")
        return False
    
    _, saved_column, saved_width, saved_active_secondary_window_id = get_current_state()
    
    # Unset glance workspace name
    niri.send_action({"UnsetWorkspaceName": {"reference": {"Name": GLANCE_WORKSPACE_NAME}}})
    
    niri.send_action({"FocusWindow": {"id": window_id}})
    
    # Restore saved width if available
    if saved_width:
        niri.send_action({"SetColumnWidth": {"change": {"SetFixed": saved_width}}})
    
    # Move column to primary monitor
    niri.send_action({"MoveColumnToWorkspaceUp": {"focus": True}})
    niri.send_action({"MoveColumnToWorkspace": {"reference": {"Name": PRIMARY_WORKSPACE}, "focus": True}})
    
    # Restore saved column position
    if saved_column is not None:
        niri.send_action({"MoveColumnToIndex": {"index": saved_column}})
    
    # Restore focus to the saved secondary window, then back to target window
    if saved_active_secondary_window_id is not None:
        log.info("Restoring focus to secondary window: %s", saved_active_secondary_window_id)
        niri.send_action({"FocusWindow": {"id": saved_active_secondary_window_id}})
    
    niri.send_action({"FocusWindow": {"id": window_id}})

    save_state("primary")
    return True

def move_to_glance():
    log.info("=== Moving to glance layout ===")
    window_id, column_index, width = find_target_window()
    if not window_id:
        log.error("Cannot move to glance: window not found")
        return False
    
    # Get secondary monitor workspace information
    secondary_info = get_workspace_info(SECONDARY_MONITOR_NAME)
    focused_window_info = niri.send_request("FocusedWindow")
    
    
    # Focus the target workspace and set its name (using workspace ID)
    niri.send_action({"FocusMonitor": {"output": SECONDARY_MONITOR_NAME}})
    niri.send_action({"SetWorkspaceName": {"name": GLANCE_WORKSPACE_NAME, "reference": {"Index": secondary_info['last_workspace_idx']}}})
    
    # Focus window, set to full width and move to secondary monitor
    niri.send_action({"FocusWindow": {"id": window_id}})
    niri.send_action({"SetWindowWidth": {"id": window_id, "change": {"SetProportion": 100.0}}})
    niri.send_action({"MoveColumnToWorkspace": {"reference": {"Name": GLANCE_WORKSPACE_NAME}, "focus": True}})
    
    if not secondary_info["focused"]:
        niri.send_action({"FocusWindow": {"id": focused_window_info["id"]}})

    # Save current state
    save_state("glance", column_index, width, secondary_info['active_window_id'])
    return True

def toggle():
    log.info("=== Toggle called ===")
    state, _, _, _ = get_current_state()
    if state == "primary":
        log.info("Toggling from primary to glance")
        return move_to_glance()
    else:
        log.info("Toggling from glance to primary")
        return move_to_primary()

def main(args=None):
    """Main entry point for window glancer.
    
    Args:
        args: List of arguments (defaults to sys.argv[1:])
    """
    if args is None:
        args = sys.argv[1:]
    
    log.info("Script started with args: %s", args)
    
    if len(args) > 0:
        cmd = args[0]
        if cmd == "primary":
            success = move_to_primary()
        elif cmd == "glance":
            success = move_to_glance()
        elif cmd == "toggle":
            success = toggle()
        else:
            print(f"Usage: window-glancer [primary|glance|toggle]", file=sys.stderr)
            return 1
    else:
        success = toggle()
    
    log.info("Script finished with success=%s", success)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())


