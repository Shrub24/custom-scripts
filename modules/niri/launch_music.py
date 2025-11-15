#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#   "pyxdg == 0.28"
# ]
# ///
import subprocess
import sys
import time
from .niri_helpers import NiriScriptConfig, NiriIPC

# Initialize script configuration
script_config = NiriScriptConfig("niri", "launch-music", load_config=True)
log = script_config.setup_logging(level="INFO")
niri = NiriIPC()
    
# Load configuration from config.toml
APP_ID_STRINGS = script_config.get_config_value("app_id_strings")
PROFILE_SUFFIX = script_config.get_config_value("profile_suffix")
BRAVE_PATH = script_config.get_config_value("brave_path")
WORKSPACE_NAME = script_config.get_config_value("workspace_name")
WAIT_TIMEOUT_SECONDS = script_config.get_config_value("wait_timeout_seconds")

# Build profile args from config
BRAVE_PROFILE_ARGS = [
    f"--profile-directory={PROFILE_SUFFIX.replace('_', ' ')}",
]

# --- SCRIPT LOGIC ---

def get_niri_state():
    """Fetches all workspaces and windows from niri using IPC."""
    workspaces = niri.send_request("Workspaces")
    windows = niri.send_request("Windows")
    return workspaces, windows


def main():
    """Main script logic."""
    log.info("--- Music Launcher Script Started ---")

    niri_app_id_map = {
        id_str: f"brave-{id_str}-{PROFILE_SUFFIX}"
        for id_str in APP_ID_STRINGS
    }
    expected_count = len(APP_ID_STRINGS)

    # --- 1. GET WORKSPACE ID ---
    log.info("Finding workspace '%s'...", WORKSPACE_NAME)
    workspaces, all_windows = get_niri_state()

    workspace_id = None
    for ws in workspaces:
        if ws.get("name") == WORKSPACE_NAME:
            workspace_id = ws.get("id")
            break

    if workspace_id is None:
        log.error("Could not find named workspace '%s'", WORKSPACE_NAME)
        return 1
    log.info("Found workspace ID: %s", workspace_id)

    # --- 2. CHECK FOR EXISTING APPS ---
    log.info("Checking for running music apps...")
    window_map = {}
    apps_to_launch = []

    for id_str in APP_ID_STRINGS:
        niri_app_id = niri_app_id_map[id_str]
        found_window = None
        for window in all_windows:
            if (window.get("app_id") == niri_app_id and
                window.get("workspace_id") == workspace_id and
                not window.get("is_floating")):
                found_window = window
                break
        
        if found_window:
            win_id = found_window['id']
            log.info("  - Found %s (ID: %s)", id_str, win_id)
            window_map[id_str] = win_id
        else:
            log.info("  - %s not found. Queued for launch", id_str)
            apps_to_launch.append(id_str)

    # ---
    # 3. EXIT IF ALL APPS ARE ALREADY RUNNING (New Logic)
    # ---
    if not apps_to_launch:
        log.info("All apps are already running. Focusing workspace and first app.")
        
        # 1. Focus the workspace
        niri.send_action({"FocusWorkspace": WORKSPACE_NAME})
        
        # 2. Focus the first app in the list for convenience
        first_window_id = window_map.get(APP_ID_STRINGS[0])
        if first_window_id:
            log.info("Focusing first window (ID: %s)", first_window_id)
            niri.send_action({"FocusWindow": {"id": first_window_id}})
        else:
            log.error("Could not find first window ID in map")
            
        return 0 # Exit the script

    # --- 4. LAUNCH MISSING APPS ---
    log.info("Launching missing apps...")
    with open(script_config.log_file, 'a', encoding='utf-8') as log_file_handle:
        for id_to_launch in apps_to_launch:
            time.sleep(0.1) # Slight delay to allow singleton instance processing 
            cmd = [BRAVE_PATH] + BRAVE_PROFILE_ARGS + [f"--app-id={id_to_launch}"]
            log.info("  - Launching: %s", ' '.join(cmd))
            
            try:
                subprocess.Popen(cmd, stdout=log_file_handle, stderr=log_file_handle)
            except OSError as e:
                log.error("Popen failed for %s: %s", id_to_launch, e)

    # --- 5. WAIT FOR NEWLY LAUNCHED APPS ---
    log.info("Waiting for newly launched apps...")
    start_time = time.time()

    while len(window_map) < expected_count:
        if time.time() - start_time > WAIT_TIMEOUT_SECONDS:
            log.error("Timed out waiting for all apps to launch. Check %s for errors", script_config.log_file)
            return 1
        
        time.sleep(0.2)
        _, all_windows = get_niri_state()

        for id_str in apps_to_launch:
            if id_str not in window_map:
                niri_app_id = niri_app_id_map[id_str]
                for window in all_windows:
                    if (window.get("app_id") == niri_app_id and
                        window.get("workspace_id") == workspace_id and
                        not window.get("is_floating")):
                        
                        win_id = window['id']
                        log.info("  - ... found new app %s (ID: %s)", id_str, win_id)
                        window_map[id_str] = win_id
                        break

    log.info("All apps are running. Finding leftmost and stacking...")

    # --- 6. Find the Leftmost Window ---
    _, all_windows = get_niri_state()
    target_windows = []
    niri_app_ids = set(niri_app_id_map.values())

    for window in all_windows:
        if (window.get("app_id") in niri_app_ids and
            window.get("workspace_id") == workspace_id and
            not window.get("is_floating")):
            target_windows.append(window)

    if len(target_windows) != expected_count:
        log.error("Expected %s windows, but found %s", expected_count, len(target_windows))
        return 1
        
    try:
        leftmost_window = min(target_windows, key=lambda w: w['layout']['pos_in_scrolling_layout'][0])
    except (KeyError, TypeError, ValueError) as e:
        log.error("Could not parse window layout to find leftmost: %s", e)
        return 1

    leftmost_id = leftmost_window['id']
    log.info("Leftmost window is ID %s (col %s)", leftmost_id, leftmost_window['layout']['pos_in_scrolling_layout'][0])

    # ---
    # 7. FOCUS, STACK, MOVE, AND REVEAL (Fast Burst)
    # ---
    log.info("Switching to workspace and starting fast-burst...")

    # === BEGIN FAST BURST ===
    
    # 1. Focus the leftmost window. This switches to 'home'.
    niri.send_action({"FocusWindow": {"id": leftmost_id}})
    
    # 2. Consume the N-1 windows to its right.
    for _ in range(expected_count - 1):
        niri.send_action({"ConsumeWindowIntoColumn": {}})
        
    # 3. Move the *entire* finished stack to the first column.
    niri.send_action({"MoveColumnToFirst": {}})
    
    log.info("Stack created. Revealing...")

    # 4. Reveal the windows.
    for win_id in window_map.values():
        niri.send_action({"FocusWindow": {"id": win_id}})
        niri.send_action({"ToggleWindowRuleOpacity": {}})
        
    # 5. Optional: Focus the window you want active first
    niri.send_action({"FocusWindow": {"id": leftmost_id}})

    # === END FAST BURST ===

    log.info("Music stack created and revealed.")
    log.info("--- Music Launcher Script Finished ---")
    return 0

if __name__ == "__main__":
    sys.exit(main())


