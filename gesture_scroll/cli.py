"""CLI and main loop for gesture-scroll (eye-close to scroll)."""
from __future__ import annotations

import argparse
import os
import sys
from collections import deque
from pathlib import Path

if "MPLCONFIGDIR" not in os.environ:
    _mpl_dir = Path(__file__).resolve().parent.parent / ".mplcache"
    _mpl_dir.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(_mpl_dir)

import cv2
import pyautogui

from gesture_scroll.camera import open_camera, frames
from gesture_scroll.face import FaceMeshDetector, FaceResult, draw_landmarks, is_looking_straight
from gesture_scroll.scroll import perform_scroll
from gesture_scroll.recorder import GestureRecorder

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
import config as project_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scroll with your eyes: keep left eye closed = up, right = down. Blinks ignored."
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Disable camera preview window.",
    )
    parser.add_argument(
        "--record",
        type=str,
        default=None,
        metavar="FILE",
        help="Record scroll events to CSV.",
    )
    parser.add_argument(
        "--record-landmarks",
        action="store_true",
        help="When recording, include nose/face landmark coordinates.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        metavar="ID",
        help="Camera device ID (default 0).",
    )
    parser.add_argument(
        "--closed-threshold",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Eye closed blend threshold 0–1 (default from config).",
    )
    parser.add_argument(
        "--hold-frames",
        type=int,
        default=None,
        metavar="N",
        help="Frames eye must stay closed to scroll (default from config).",
    )
    parser.add_argument(
        "--scroll-amount",
        type=int,
        default=None,
        metavar="N",
        help="Scroll steps per tick (default from config).",
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save current options to config.json and exit.",
    )
    return parser.parse_args()


def _skip_reason(result: FaceResult, nose_x_min: float, nose_x_max: float, nose_y_min: float, nose_y_max: float, max_head_pitch_deg: float) -> str | None:
    """Return why detection is skipped, or None if looking straight."""
    if result.nose_x is None or result.nose_y is None or result.eye_blink_left is None or result.eye_blink_right is None:
        return "No face"
    if result.head_pitch_deg is not None and abs(result.head_pitch_deg) > max_head_pitch_deg:
        return "Head pitch"
    if not (nose_x_min <= result.nose_x <= nose_x_max and nose_y_min <= result.nose_y <= nose_y_max):
        return "Nose out of zone"
    return None


def _draw_debug_overlay(
    frame: cv2.typing.MatLike,
    result: FaceResult,
    *,
    looking_straight: bool,
    left_closed_frames: int,
    right_closed_frames: int,
    closed_threshold: float,
    hold_frames: int,
    look_straight: tuple[float, float, float, float, float],
    big_message: str = "",
) -> None:
    """Draw debug variables and look-straight zone on the preview frame."""
    nose_x_min, nose_x_max, nose_y_min, nose_y_max, max_head_pitch_deg = look_straight
    h, w = frame.shape[:2]
    x1 = int(nose_x_min * w)
    y1 = int(nose_y_min * h)
    x2 = int(nose_x_max * w)
    y2 = int(nose_y_max * h)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # Big status text (scroll action or skip reason) – top-center, large
    if big_message:
        font_big = cv2.FONT_HERSHEY_SIMPLEX
        scale_big = 2.2
        thickness_big = 5
        (tw, th), _ = cv2.getTextSize(big_message, font_big, scale_big, thickness_big)
        tx = (w - tw) // 2
        ty = 60 + th
        # Outline for readability
        for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            cv2.putText(frame, big_message, (tx + dx, ty + dy), font_big, scale_big, (0, 0, 0), thickness_big)
        color_big = (0, 255, 0) if big_message.startswith("SCROLL") else (0, 165, 255)
        cv2.putText(frame, big_message, (tx, ty), font_big, scale_big, color_big, thickness_big)

    # Variables list – larger text
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.5
    thickness = 3
    color = (0, 255, 0)
    y_step = 48
    x, y = 10, 120

    def put(line: str) -> None:
        nonlocal y
        cv2.putText(frame, line, (x, y), font, scale, color, thickness)
        y += y_step

    nose_x = result.nose_x if result.nose_x is not None else None
    nose_y = result.nose_y if result.nose_y is not None else None
    left = result.eye_blink_left
    right = result.eye_blink_right

    put(f"nose_x: {nose_x:.3f}" if nose_x is not None else "nose_x: N/A")
    put(f"nose_y: {nose_y:.3f}" if nose_y is not None else "nose_y: N/A")
    put(f"eye_L: {left:.3f}" if left is not None else "eye_L: N/A")
    put(f"eye_R: {right:.3f}" if right is not None else "eye_R: N/A")
    head_pitch = result.head_pitch_deg
    put(f"head_pitch_deg: {head_pitch:.1f}" if head_pitch is not None else "head_pitch_deg: N/A")
    put(f"max_head_pitch_deg: {max_head_pitch_deg}")
    put(f"looking_straight: {looking_straight}")
    put(f"closed_threshold: {closed_threshold}")
    put(f"hold_frames: {hold_frames}")
    put(f"left_closed_frames: {left_closed_frames}")
    put(f"right_closed_frames: {right_closed_frames}")


def apply_args_to_config(cfg: dict, args: argparse.Namespace) -> dict:
    if args.closed_threshold is not None:
        cfg["closed_threshold"] = args.closed_threshold
    if args.hold_frames is not None:
        cfg["hold_frames"] = args.hold_frames
    if args.scroll_amount is not None:
        cfg["scroll_amount"] = args.scroll_amount
    return cfg


def main() -> None:
    args = parse_args()
    cfg = project_config.load_config()
    cfg = apply_args_to_config(cfg, args)

    if args.save_config:
        project_config.save_config(cfg)
        print("Config saved to", project_config.CONFIG_PATH)
        return

    try:
        cap = open_camera(args.camera)
    except RuntimeError:
        print("Error: Could not open camera.", file=sys.stderr)
        print("On macOS: grant Camera in System Settings → Privacy & Security → Camera.", file=sys.stderr)
        print("Try --camera 1 for a different device.", file=sys.stderr)
        sys.exit(1)

    closed_threshold = cfg["closed_threshold"]
    hold_frames = cfg["hold_frames"]
    scroll_every_n = cfg["scroll_every_n_frames"]
    scroll_amount = cfg["scroll_amount"]
    look_straight = (
        cfg["look_straight_nose_x_min"],
        cfg["look_straight_nose_x_max"],
        cfg["look_straight_nose_y_min"],
        cfg["look_straight_nose_y_max"],
        cfg["look_straight_max_head_pitch_deg"],
    )

    print("Gesture Scroll – keep left eye closed = scroll up, right = scroll down. Blinks do nothing.")
    print("On macOS: enable Accessibility for Terminal/Cursor. Press 'q' in preview to quit.")

    recorder: GestureRecorder | None = None
    if args.record:
        recorder = GestureRecorder(args.record, record_landmarks=args.record_landmarks)
        recorder.start()
        print("Recording to", args.record)

    show_preview = not args.no_preview
    detector = None
    left_closed_frames = 0
    right_closed_frames = 0
    # History of (left_closed, right_closed) over last hold_frames to reject blinks
    eye_history: deque[tuple[bool, bool]] = deque(maxlen=hold_frames)
    try:
        detector = FaceMeshDetector()
        for ret, frame in frames(cap):
            if not ret or frame is None:
                break
            result = detector.process(frame)
            left = result.eye_blink_left
            right = result.eye_blink_right
            debug_big_message = ""

            # Only use closed-eye detection when looking straight at the camera
            if not is_looking_straight(result, *look_straight) or left is None or right is None:
                left_closed_frames = 0
                right_closed_frames = 0
                eye_history.clear()
                reason = _skip_reason(result, *look_straight)
                if reason:
                    debug_big_message = f"SKIP: {reason}"
            else:
                left_closed = left > closed_threshold
                right_closed = right > closed_threshold
                eye_history.append((left_closed, right_closed))
                if left_closed:
                    left_closed_frames += 1
                else:
                    left_closed_frames = 0
                if right_closed:
                    right_closed_frames += 1
                else:
                    right_closed_frames = 0

                # Scroll only if other eye was never closed in last hold_frames (reject blinks)
                if left_closed_frames >= hold_frames and not right_closed:
                    if not any(r for (_, r) in eye_history):
                        if (left_closed_frames - hold_frames) % scroll_every_n == 0:
                            try:
                                perform_scroll(0, scroll_amount)
                                debug_big_message = "SCROLL UP"
                            except pyautogui.FailSafeException:
                                print("\nFail-safe triggered (mouse in corner). Quitting.")
                                break
                            if recorder is not None:
                                recorder.write_frame(
                                    scroll_dx=0, scroll_dy=scroll_amount, nose_dx=0, nose_dy=0,
                                    nose_x=result.nose_x, nose_y=result.nose_y,
                                    face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                                )
                    else:
                        debug_big_message = "SKIP: Blink"
                elif right_closed_frames >= hold_frames and not left_closed:
                    if not any(l for (l, _) in eye_history):
                        if (right_closed_frames - hold_frames) % scroll_every_n == 0:
                            try:
                                perform_scroll(0, -scroll_amount)
                                debug_big_message = "SCROLL DOWN"
                            except pyautogui.FailSafeException:
                                print("\nFail-safe triggered (mouse in corner). Quitting.")
                                break
                            if recorder is not None:
                                recorder.write_frame(
                                    scroll_dx=0, scroll_dy=-scroll_amount, nose_dx=0, nose_dy=0,
                                    nose_x=result.nose_x, nose_y=result.nose_y,
                                    face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                                )
                    else:
                        debug_big_message = "SKIP: Blink"

            if show_preview:
                draw_landmarks(frame, result.landmarks)
                # Debug overlay
                looking_straight = is_looking_straight(result, *look_straight)
                _draw_debug_overlay(
                    frame, result,
                    looking_straight=looking_straight,
                    left_closed_frames=left_closed_frames,
                    right_closed_frames=right_closed_frames,
                    closed_threshold=closed_threshold,
                    hold_frames=hold_frames,
                    look_straight=look_straight,
                    big_message=debug_big_message,
                )
                cv2.imshow("Gesture Scroll", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        if detector is not None:
            detector.close()
    finally:
        cap.release()
        if recorder is not None:
            recorder.stop()
        if show_preview:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
