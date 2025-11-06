#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = [
#   "pyxdg == 0.28"
# ]
# ///
"""
Like open-float, but dynamically. Floats a window when it matches the rules.
Some windows don't have the right title and app-id when they open, and only set
them afterward. This script is like open-float for those windows.
Usage: Configure rules in dynamic-float.toml
"""

from dataclasses import dataclass, field
import json
import os
import re
from socket import AF_UNIX, SHUT_WR, socket
from niri_helpers import NiriScriptConfig, NiriIPC

# Initialize script configuration
script_config = NiriScriptConfig("dynamic-float", load_config=True)
log = script_config.setup_logging(level="DEBUG")
niri = NiriIPC()

@dataclass(kw_only=True)
class Match:
    title: str | None = None
    app_id: str | None = None

    def matches(self, window):
        if self.title is None and self.app_id is None:
            return False

        matched = True

        if self.title is not None:
            matched &= re.search(self.title, window["title"]) is not None
        if self.app_id is not None:
            matched &= re.search(self.app_id, window["app_id"]) is not None

        return matched


@dataclass
class Rule:
    match: list[Match] = field(default_factory=list)
    exclude: list[Match] = field(default_factory=list)
    width: int = 0
    height: int = 0
    centered: bool = False

    def matches(self, window):
        if len(self.match) > 0 and not any(m.matches(window) for m in self.match):
            return False
        if any(m.matches(window) for m in self.exclude):
            return False

        return True


def load_rules_from_config():
    """Load rules from TOML configuration."""
    rules = []
    config_rules = script_config.config.get("rules", [])
    
    for rule_config in config_rules:
        title = rule_config.get("title")
        app_id = rule_config.get("app_id")
        width = rule_config.get("width")
        height = rule_config.get("height")
        centered = rule_config.get("centered")
        
        match = Match(title=title, app_id=app_id)
        rule = Rule(match=[match], width=width or 0, height=height or 0, centered=centered or False)
        rules.append(rule)
    
    return rules

RULES = load_rules_from_config()

if not RULES:
    log.error("No rules configured in dynamic-float.toml")
    raise SystemExit(1)


# Setup event stream
niri_socket = socket(AF_UNIX)
niri_socket.connect(os.environ["NIRI_SOCKET"])
file = niri_socket.makefile("rw")

_ = file.write('"EventStream"')
file.flush()
niri_socket.shutdown(SHUT_WR)

windows = {}


def float_window(window_id: int):
    """Float a window."""
    niri.send_action({"MoveWindowToFloating": {"id": window_id}})

def set_height(window_id: int, height: int):
    """Set window height."""
    niri.send_action({"SetWindowHeight": {"id": window_id, "change": {"SetFixed": height}}})

def set_width(window_id: int, width: int):
    """Set window width."""
    niri.send_action({"SetWindowWidth": {"id": window_id, "change": {"SetFixed": width}}})

def set_centered(window_id: int, width: int, height: int):
    """Center a window on screen."""
    # move window to center of the screen
    niri.send_action({"MoveFloatingWindow": 
                      {"id": window_id, "x": {"SetProportion": 50.0}, "y": {"SetProportion": 50.0}}})

    # adjust for top left origin
    niri.send_action({"MoveFloatingWindow":
                      {"id": window_id, "x": {"AdjustFixed": -(width / 2)}, "y": {"AdjustFixed": height/4}}})

def update_matched(window):
    """Check if window matches any rules and apply floating/sizing."""
    window["matched"] = False
    if existing := windows.get(window["id"]):
        window["matched"] = existing["matched"]

    matched_before = window["matched"]
    matched_rule = None
    for rule in RULES:
        if rule.matches(window):
            window["matched"] = True
            matched_rule = rule
            break
    
    if window["matched"] and not matched_before and matched_rule:
        log.info("Floating window: title=%s, app_id=%s", window['title'], window['app_id'])
        window_id = window["id"]
        float_window(window_id)
        if matched_rule.height:
            set_height(window_id, matched_rule.height)
        if matched_rule.width:
            set_width(window_id, matched_rule.width)
        if matched_rule.centered:
            set_centered(window_id, matched_rule.width, matched_rule.height)


for line in file:
    event = json.loads(line)

    if changed := event.get("WindowsChanged"):
        for win in changed["windows"]:
            update_matched(win)
        windows = {win["id"]: win for win in changed["windows"]}
    elif changed := event.get("WindowOpenedOrChanged"):
        win = changed["window"]
        update_matched(win)
        windows[win["id"]] = win
    elif changed := event.get("WindowClosed"):
        del windows[changed["id"]]

