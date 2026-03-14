"""Map position deltas to PyAutoGUI scroll with sensitivity, dead zone, smoothing."""
from __future__ import annotations

import pyautogui

# Reduce accidental triggers
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


class ScrollController:
    """Converts normalized (dx, dy) face movement into scroll events with smoothing."""

    def __init__(
        self,
        sensitivity: float = 1.0,
        dead_zone: float = 0.02,
        scroll_scale: float = 50.0,
        max_scroll_per_frame: float = 15.0,
        smoothing_alpha: float = 0.3,
        scroll_vertical: bool = True,
        scroll_horizontal: bool = False,
        invert_vertical: bool = False,
        invert_horizontal: bool = False,
    ):
        self.sensitivity = sensitivity
        self.dead_zone = dead_zone
        self.scroll_scale = scroll_scale
        self.max_scroll_per_frame = max_scroll_per_frame
        self.smoothing_alpha = smoothing_alpha
        self.scroll_vertical = scroll_vertical
        self.scroll_horizontal = scroll_horizontal
        self.invert_vertical = invert_vertical
        self.invert_horizontal = invert_horizontal
        self._smoothed_dx = 0.0
        self._smoothed_dy = 0.0

    def _apply_dead_zone(self, value: float) -> float:
        if abs(value) < self.dead_zone:
            return 0.0
        if value > 0:
            return value - self.dead_zone
        return value + self.dead_zone

    def _smooth(self, new_dx: float, new_dy: float) -> tuple[float, float]:
        self._smoothed_dx = (
            self.smoothing_alpha * new_dx + (1 - self.smoothing_alpha) * self._smoothed_dx
        )
        self._smoothed_dy = (
            self.smoothing_alpha * new_dy + (1 - self.smoothing_alpha) * self._smoothed_dy
        )
        return self._smoothed_dx, self._smoothed_dy

    def update(self, dx: float, dy: float) -> tuple[float, float]:
        """
        Given normalized deltas (e.g. from nose movement), return (scroll_x, scroll_y)
        in scroll units (clicks). Apply dead zone, smoothing, sensitivity, clamp.
        """
        dx = self._apply_dead_zone(dx)
        dy = self._apply_dead_zone(dy)
        dx, dy = self._smooth(dx, dy)

        scale = self.sensitivity * self.scroll_scale
        sx = dx * scale if self.scroll_horizontal else 0.0
        sy = dy * scale if self.scroll_vertical else 0.0

        if self.invert_vertical:
            sy = -sy
        if self.invert_horizontal:
            sx = -sx

        max_s = self.max_scroll_per_frame
        sx = max(-max_s, min(max_s, sx))
        sy = max(-max_s, min(max_s, sy))

        return sx, sy

    def perform_scroll(self, scroll_x: float, scroll_y: float) -> None:
        """Emit PyAutoGUI scroll at current cursor position."""
        if scroll_y != 0:
            pyautogui.scroll(int(round(scroll_y)))
        if scroll_x != 0:
            pyautogui.hscroll(int(round(scroll_x)))
