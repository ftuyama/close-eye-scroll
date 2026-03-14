"""Configuration defaults and load/save from config.json."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS = {
    "closed_threshold": 0.4,
    "hold_frames": 8,
    "scroll_every_n_frames": 1,
    "scroll_amount": 1,
    "look_straight_nose_x_min": 0.35,
    "look_straight_nose_x_max": 0.65,
    "look_straight_nose_y_min": 0.35,
    "look_straight_nose_y_max": 0.55,
    "look_straight_max_head_pitch_deg": 15.0,
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
