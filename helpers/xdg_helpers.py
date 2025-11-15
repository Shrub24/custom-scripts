"""XDG Base Directory helpers for locating application config files."""

from pathlib import Path
from xdg import BaseDirectory


def get_xdg_config_file(application: str, filename: str) -> Path:
    """Get the path to an application's config file using XDG Base Directory spec.
    
    Args:
        application: Name of the application (e.g., 'zellij', 'nvim')
        filename: Name of the config file (e.g., 'config.kdl', 'init.lua')
        
    Returns:
        Path to the config file (may not exist)
        
    Examples:
        >>> get_xdg_config_file('zellij', 'config.kdl')
        PosixPath('/home/user/.config/zellij/config.kdl')
    """
    config_dir = Path(BaseDirectory.xdg_config_home) / application
    return config_dir / filename
