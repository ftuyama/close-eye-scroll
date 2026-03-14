"""Configuration defaults and load/save from config.json."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS = {
    "sensitivity": 1.0,
    "dead_zone": 0.02,
    "scroll_scale": 50.0,
    "max_scroll_per_frame": 15,
    "smoothing_alpha": 0.3,
    "scroll_vertical": True,
    "scroll_horizontal": False,
    "invert_vertical": False,
    "invert_horizontal": False,
}


def load_config(path: Path | None = None) -> dict:
    """Load config from JSON file or return defaults."""
    p = path or CONFIG_PATH
    if p.exists():
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULTS.copy()


def save_config(config: dict, path: Path | None = None) -> None:
    """Save config to JSON file."""
    p = path or CONFIG_PATH
    with open(p, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
