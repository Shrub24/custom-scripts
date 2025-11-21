#!/usr/bin/env python3
"""Theme management module for generating color schemes from wallpapers."""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

from helpers import ScriptConfig
from .apply_zellij_theme import apply_zellij_theme


def run_matugen(wallpaper_path: Path) -> dict:
    """Run matugen to extract colors from wallpaper.
    
    Args:
        wallpaper_path: Path to the wallpaper image
        
    Returns:
        Dictionary containing color data from matugen
        
    Raises:
        subprocess.CalledProcessError: If matugen fails
        json.JSONDecodeError: If output is not valid JSON
    """
    import tempfile
    
    logging.debug("Running matugen to extract colors...")
    
    # Create temporary config file to avoid errors
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write('[config]\nmode = "dark"\nscheme_type = "scheme-fidelity"\n\n[templates]\n')
        config_file = f.name
    
    try:
        result = subprocess.run(
            [
                "matugen",
                "image",
                str(wallpaper_path),
                "--json",
                "hex",
                "-m",
                "dark",
                "-t",
                "scheme-fidelity",
                "--include-image-in-json",
                "false",
                "--dry-run",
                "-c",
                config_file,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        
        data = json.loads(result.stdout)
        logging.debug(f"Matugen output parsed successfully")
        
        return data
    finally:
        # Clean up temp file
        Path(config_file).unlink(missing_ok=True)


def run_dms_dank16(primary_hex: str, surface_hex: str) -> dict:
    """Generate 16-color scheme using dms dank16.
    
    Args:
        primary_hex: Primary color in hex format
        surface_hex: Surface/background color in hex format
        
    Returns:
        Dictionary containing the 16-color palette
        
    Raises:
        subprocess.CalledProcessError: If dms fails
        json.JSONDecodeError: If output is not valid JSON
    """
    logging.debug(f"Generating dank16 scheme (primary: {primary_hex}, surface: {surface_hex})...")
    
    result = subprocess.run(
        [
            "dms",
            "dank16",
            primary_hex,
            f"--background={surface_hex}",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    
    data = json.loads(result.stdout)
    logging.debug(f"dms output: {json.dumps(data)}")
    
    return data


def run_matugen_with_templates(wallpaper_path: Path, dank16_colors: dict, config_path: Path) -> None:
    """Run matugen with user templates and dank16 colors.
    
    Args:
        wallpaper_path: Path to the wallpaper image
        dank16_colors: Dictionary containing dank16 color palette
        config_path: Path to user's matugen config file
        
    Raises:
        subprocess.CalledProcessError: If matugen fails
    """
    logging.debug("Running matugen with user templates...")
    
    # Wrap dank16 colors in expected structure
    import_data = {"dank16": dank16_colors}
    import_json = json.dumps(import_data)
    
    logging.debug(f"Import JSON: {import_json}")
    
    subprocess.run(
        [
            "matugen",
            "image",
            str(wallpaper_path),
            "-c",
            str(config_path),
            "--import-json-string",
            import_json,
        ],
        check=True,
    )
    
    logging.debug("User templates processed successfully")


def wallpaper_changed(wallpaper_path: Path, verbose: bool = False) -> None:
    """Process wallpaper change and generate color schemes.
    
    Args:
        wallpaper_path: Path to the wallpaper image
        verbose: Enable verbose logging
        
    Raises:
        FileNotFoundError: If wallpaper or config file not found
        subprocess.CalledProcessError: If any command fails
    """
    # Initialize config and logging
    module_dir = Path(__file__).resolve().parent
    config = ScriptConfig(
        module_name="theme",
        script_name="wallpaper-changed",
        load_config=True,
        module_dir=module_dir
    )
    
    # Setup logging - debug to file, verbose controls console
    log_level = logging.DEBUG if verbose else logging.INFO
    config.setup_logging(level=log_level, include_console=verbose)
    
    logger = logging.getLogger("wallpaper-changed")
    logger.info(f"Processing wallpaper: {wallpaper_path}")
    
    if not wallpaper_path.exists():
        raise FileNotFoundError(f"Wallpaper file not found: {wallpaper_path}")
    
    # Extract colors from wallpaper
    matugen_data = run_matugen(wallpaper_path)
    primary_hex = matugen_data["colors"]["primary"]["dark"]
    surface_hex = matugen_data["colors"]["surface"]["dark"]
    
    logger.info(f"Primary color: {primary_hex}")
    logger.info(f"Surface color: {surface_hex}")
    
    # Generate 16-color scheme
    dank16_colors = run_dms_dank16(primary_hex, surface_hex)
    
    # Apply templates with user config
    user_config = config.get_config_path("matugen-config.toml")
    
    if not user_config.exists():
        logger.warning(f"User config not found at {user_config}")
        logger.warning("Skipping final theme generation.")
        return
    
    run_matugen_with_templates(wallpaper_path, dank16_colors, user_config)
    
    logger.info("Color schemes generated successfully!")
    
    # Run post-processing scripts to apply themes to running applications
    # run_post_processing(config, verbose)


def run_post_processing(config: ScriptConfig, verbose: bool = False) -> None:
    """Run post-processing scripts to apply themes to applications.
    
    Args:
        config: ScriptConfig instance with module_dir set
        verbose: Enable verbose logging for post-processing scripts
    """
    logger = logging.getLogger("wallpaper-changed")
    logger.info("Running post-processing scripts...")
    
    if config.module_dir is None:
        logger.warning("Module directory not set, skipping post-processing")
        return
    
    # Apply Zellij theme
    try:        
        # Get theme names from config
        theme_name = config.get_config_value("zellij_theme", default="dankcolors")
        theme_alt = config.get_config_value("zellij_theme_alt", default="dankcolors-alt")
        
        apply_zellij_theme(theme_name, theme_alt)
        logger.debug("Zellij post-processing completed")
    except Exception as e:
        logger.warning(f"Zellij post-processing failed: {e}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process wallpaper and generate color schemes"
    )
    parser.add_argument(
        "wallpaper",
        type=Path,
        help="Path to the wallpaper image",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    try:
        wallpaper_changed(args.wallpaper, args.verbose)
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed: {e.cmd}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return e.returncode
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON output: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
