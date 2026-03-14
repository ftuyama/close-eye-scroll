"""CLI and main loop for gesture-scroll (eye-close to scroll)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if "MPLCONFIGDIR" not in os.environ:
    _mpl_dir = Path(__file__).resolve().parent.parent / ".mplcache"
    _mpl_dir.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(_mpl_dir)

import cv2
import pyautogui

from gesture_scroll.camera import open_camera, frames
from gesture_scroll.face import FaceMeshDetector, draw_landmarks, is_looking_straight
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
    try:
        detector = FaceMeshDetector()
        for ret, frame in frames(cap):
            if not ret or frame is None:
                break
            result = detector.process(frame)
            left = result.eye_blink_left
            right = result.eye_blink_right

            # Only use closed-eye detection when looking straight at the camera
            if not is_looking_straight(result, *look_straight) or left is None or right is None:
                left_closed_frames = 0
                right_closed_frames = 0
            else:
                left_closed = left > closed_threshold
                right_closed = right > closed_threshold
                if left_closed:
                    left_closed_frames += 1
                else:
                    left_closed_frames = 0
                if right_closed:
                    right_closed_frames += 1
                else:
                    right_closed_frames = 0

                if left_closed_frames >= hold_frames and not right_closed:
                    if (left_closed_frames - hold_frames) % scroll_every_n == 0:
                        try:
                            perform_scroll(0, scroll_amount)
                        except pyautogui.FailSafeException:
                            print("\nFail-safe triggered (mouse in corner). Quitting.")
                            break
                        if recorder is not None:
                            recorder.write_frame(
                                scroll_dx=0, scroll_dy=scroll_amount,
                                nose_dx=0, nose_dy=0,
                                nose_x=result.nose_x, nose_y=result.nose_y,
                                face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                            )
                elif right_closed_frames >= hold_frames and not left_closed:
                    if (right_closed_frames - hold_frames) % scroll_every_n == 0:
                        try:
                            perform_scroll(0, -scroll_amount)
                        except pyautogui.FailSafeException:
                            print("\nFail-safe triggered (mouse in corner). Quitting.")
                            break
                        if recorder is not None:
                            recorder.write_frame(
                                scroll_dx=0, scroll_dy=-scroll_amount,
                                nose_dx=0, nose_dy=0,
                                nose_x=result.nose_x, nose_y=result.nose_y,
                                face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                            )

            if show_preview:
                draw_landmarks(frame, result.landmarks)
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
