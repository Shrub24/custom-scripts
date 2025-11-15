#!/usr/bin/env python3
"""Apply theme to Zellij by toggling theme variants to trigger a refresh."""

import logging

from helpers import get_xdg_config_file

def apply_zellij_theme(theme_name: str, theme_alt: str) -> None:
    """Apply theme to Zellij by toggling between variants.
    
    This switches between identical theme variants (e.g., "custom" <-> "custom-alt")
    to trigger Zellij to reload the theme files.
    
    Args:
        theme_name: Base name of the theme
        theme_alt: Alternate theme name
        
    Raises:
        FileNotFoundError: If Zellij config doesn't exist
    """
    logger = logging.getLogger("wallpaper-changed")
    logger.info("Applying theme to Zellij...")
    
    config_path = get_xdg_config_file("zellij", "config.kdl")
    
    if not config_path.exists():
        logger.warning(f"Zellij config not found at {config_path}, skipping")
        return
    
    try:
        content = config_path.read_text()
        lines = content.splitlines()
        
        # Find current theme and toggle it
        modified = False
        for i, line in enumerate(lines):
            if line.strip().startswith("theme "):
                # Extract current theme
                current = line.split('"')[1] if '"' in line else None
                
                # Toggle between variants
                if current == theme_name:
                    new_theme = theme_alt
                    logger.debug(f"Switching from {theme_name} to {theme_alt}")
                else:
                    new_theme = theme_name
                    logger.debug(f"Switching to {theme_name}")
                
                lines[i] = f'theme "{new_theme}"'
                modified = True
                break
        
        if not modified:
            # If no theme line exists, add it at the top
            lines.insert(0, f'theme "{theme_name}"')
            logger.debug(f"Added theme line: {theme_name}")
        
        # Write back to config (this triggers Zellij to reload)
        config_path.write_text('\n'.join(lines) + '\n')
        logger.info("Zellij theme updated successfully")
        
    except Exception as e:
        logger.error(f"Failed to update Zellij theme: {e}")
