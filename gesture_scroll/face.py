"""MediaPipe Face Landmarker (tasks API): landmark detection and nose/face position."""
from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from mediapipe.tasks.python.core import base_options as base_options_lib
from mediapipe.tasks.python.vision import face_landmarker
from mediapipe.tasks.python.vision.core import vision_task_running_mode

# Nose tip index in MediaPipe Face Landmarker (478 landmarks)
NOSE_TIP_INDEX = 4
# Indices for face center approx (forehead, nose tip, chin)
FACE_CENTER_INDICES = (10, 4, 152)

MODEL_FILENAME = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"


def _get_model_path() -> Path:
    """Return path to face_landmarker.task; download if missing."""
    project_root = Path(__file__).resolve().parent.parent
    path = project_root / MODEL_FILENAME
    if path.exists():
        return path
    env_path = os.environ.get("GESTURE_SCROLL_FACE_MODEL")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    # Download to project root
    print(f"Downloading face landmarker model to {path}...")
    urllib.request.urlretrieve(MODEL_URL, path)
    return path


# Blendshape indices for eye blink (from face_landmarker.Blendshapes)
EYE_BLINK_LEFT_INDEX = 9
EYE_BLINK_RIGHT_INDEX = 10


@dataclass
class FaceResult:
    """Normalized (x, y) for nose tip and face center; eye blink scores 0–1; None if no face."""
    nose_x: float | None
    nose_y: float | None
    face_center_x: float | None
    face_center_y: float | None
    landmarks: Any  # list of landmark-like (x, y, z) for drawing
    eye_blink_left: float | None = None   # 0=open, higher=more closed
    eye_blink_right: float | None = None


class FaceMeshDetector:
    """MediaPipe Face Landmarker (tasks API): detect face and return nose/center (normalized 0–1)."""

    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        model_path = _get_model_path()
        base_options = base_options_lib.BaseOptions(
            model_asset_path=str(model_path),
            delegate=base_options_lib.BaseOptions.Delegate.CPU,
        )
        options = face_landmarker.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision_task_running_mode.VisionTaskRunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=min_detection_confidence,
            min_face_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_face_blendshapes=True,
        )
        self._landmarker = face_landmarker.FaceLandmarker.create_from_options(options)
        self._frame_timestamp_ms = 0

    def process(self, frame: cv2.typing.MatLike) -> FaceResult:
        """Run face landmarker on BGR frame. Returns normalized coordinates (x, y in 0–1)."""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        from mediapipe import Image, ImageFormat
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, self._frame_timestamp_ms)
        self._frame_timestamp_ms += 33  # ~30 fps

        if not result.face_landmarks:
            return FaceResult(
                nose_x=None, nose_y=None,
                face_center_x=None, face_center_y=None,
                landmarks=None,
                eye_blink_left=None,
                eye_blink_right=None,
            )

        lm_list = result.face_landmarks[0]
        nose = lm_list[NOSE_TIP_INDEX]
        nose_x, nose_y = nose.x, nose.y

        cx = sum(lm_list[i].x for i in FACE_CENTER_INDICES) / len(FACE_CENTER_INDICES)
        cy = sum(lm_list[i].y for i in FACE_CENTER_INDICES) / len(FACE_CENTER_INDICES)

        eye_blink_left = None
        eye_blink_right = None
        if result.face_blendshapes and len(result.face_blendshapes) > 0:
            categories = result.face_blendshapes[0]
            for c in categories:
                if c.index == EYE_BLINK_LEFT_INDEX and c.score is not None:
                    eye_blink_left = c.score
                elif c.index == EYE_BLINK_RIGHT_INDEX and c.score is not None:
                    eye_blink_right = c.score

        return FaceResult(
            nose_x=nose_x, nose_y=nose_y,
            face_center_x=cx, face_center_y=cy,
            landmarks=lm_list,
            eye_blink_left=eye_blink_left,
            eye_blink_right=eye_blink_right,
        )

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> "FaceMeshDetector":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def is_looking_straight(
    result: FaceResult,
    nose_x_min: float = 0.35,
    nose_x_max: float = 0.65,
    nose_y_min: float = 0.35,
    nose_y_max: float = 0.55,
) -> bool:
    """True only when face is visible and nose is in the central region (looking straight at camera)."""
    if result.nose_x is None or result.nose_y is None:
        return False
    return (
        nose_x_min <= result.nose_x <= nose_x_max
        and nose_y_min <= result.nose_y <= nose_y_max
    )


def draw_landmarks(frame: cv2.typing.MatLike, landmarks: Any) -> None:
    """Draw face landmarks on frame in-place (nose circle)."""
    if landmarks is None:
        return
    h, w = frame.shape[:2]
    nose = landmarks[NOSE_TIP_INDEX]
    px, py = int(nose.x * w), int(nose.y * h)
    cv2.circle(frame, (px, py), 6, (0, 255, 0), 2)
