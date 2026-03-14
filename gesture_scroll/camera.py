"""Webcam capture using OpenCV."""
from __future__ import annotations

import cv2
from typing import Generator


def open_camera(device_id: int = 0) -> cv2.VideoCapture:
    """Open default or specified camera. Caller must release with .release()."""
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera (device_id={device_id})")
    return cap


def frames(cap: cv2.VideoCapture) -> Generator[tuple[bool, cv2.typing.MatLike], None, None]:
    """Yield (success, frame) from the capture. BGR format."""
    while True:
        ret, frame = cap.read()
        yield ret, frame
        if not ret:
            break
