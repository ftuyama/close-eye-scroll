"""Emit scroll events via PyAutoGUI."""
from __future__ import annotations

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01


def perform_scroll(scroll_x: int | float, scroll_y: int | float) -> None:
    """Emit scroll at current cursor position. Positive y = up, negative y = down."""
    if scroll_y != 0:
        pyautogui.scroll(int(round(scroll_y)))
    if scroll_x != 0:
        pyautogui.hscroll(int(round(scroll_x)))
