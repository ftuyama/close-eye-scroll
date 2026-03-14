"""CLI: argparse and main loop for gesture-scroll."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Set writable matplotlib cache before any import that pulls in matplotlib (e.g. mediapipe)
if "MPLCONFIGDIR" not in os.environ:
    _mpl_dir = Path(__file__).resolve().parent.parent / ".mplcache"
    _mpl_dir.mkdir(exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(_mpl_dir)

import cv2

from gesture_scroll.camera import open_camera, frames
from gesture_scroll.face import FaceMeshDetector, draw_landmarks
from gesture_scroll.scroll import ScrollController
import pyautogui
from gesture_scroll.recorder import GestureRecorder

# Config lives in project root (parent of gesture_scroll package)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
import config as project_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scroll with your face: webcam + MediaPipe → PyAutoGUI scroll."
    )
    parser.add_argument(
        "--sensitivity",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Scroll sensitivity (e.g. 0.5–3.0). Overrides config.",
    )
    parser.add_argument(
        "--dead-zone",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Min movement before scrolling (normalized). Overrides config.",
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
        help="Record gesture data (deltas) to CSV file.",
    )
    parser.add_argument(
        "--record-landmarks",
        action="store_true",
        help="When recording, also save nose/face landmark coordinates.",
    )
    parser.add_argument(
        "--scroll-vertical",
        action="store_true",
        default=None,
        help="Enable vertical scroll (default: true).",
    )
    parser.add_argument(
        "--no-scroll-vertical",
        action="store_false",
        dest="scroll_vertical",
        help="Disable vertical scroll.",
    )
    parser.add_argument(
        "--scroll-horizontal",
        action="store_true",
        default=None,
        help="Enable horizontal scroll.",
    )
    parser.add_argument(
        "--invert-vertical",
        action="store_true",
        default=None,
        help="Invert vertical scroll direction.",
    )
    parser.add_argument(
        "--invert-horizontal",
        action="store_true",
        default=None,
        help="Invert horizontal scroll direction.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        metavar="ID",
        help="Camera device ID (default 0).",
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save current CLI options to config.json and exit.",
    )
    return parser.parse_args()


def apply_args_to_config(cfg: dict, args: argparse.Namespace) -> dict:
    """Merge CLI args into config; None means do not override."""
    if args.sensitivity is not None:
        cfg["sensitivity"] = args.sensitivity
    if args.dead_zone is not None:
        cfg["dead_zone"] = args.dead_zone
    if args.scroll_vertical is not None:
        cfg["scroll_vertical"] = args.scroll_vertical
    if args.scroll_horizontal is not None:
        cfg["scroll_horizontal"] = args.scroll_horizontal
    if args.invert_vertical is not None:
        cfg["invert_vertical"] = args.invert_vertical
    if args.invert_horizontal is not None:
        cfg["invert_horizontal"] = args.invert_horizontal
    return cfg


def main() -> None:
    args = parse_args()
    cfg = project_config.load_config()
    cfg = apply_args_to_config(cfg, args)

    if args.save_config:
        project_config.save_config(cfg)
        print("Config saved to", project_config.CONFIG_PATH)
        return

    scroll_ctrl = ScrollController(
        sensitivity=cfg["sensitivity"],
        dead_zone=cfg["dead_zone"],
        scroll_scale=cfg["scroll_scale"],
        max_scroll_per_frame=cfg["max_scroll_per_frame"],
        smoothing_alpha=cfg["smoothing_alpha"],
        scroll_vertical=cfg["scroll_vertical"],
        scroll_horizontal=cfg["scroll_horizontal"],
        invert_vertical=cfg["invert_vertical"],
        invert_horizontal=cfg["invert_horizontal"],
    )

    recorder: GestureRecorder | None = None
    if args.record:
        recorder = GestureRecorder(args.record, record_landmarks=args.record_landmarks)
        recorder.start()
        print("Recording to", args.record)

    try:
        cap = open_camera(args.camera)
    except RuntimeError:
        print("Error: Could not open camera.", file=sys.stderr)
        print("On macOS: grant Camera access in System Settings → Privacy & Security → Camera.", file=sys.stderr)
        print("You can try a different device with --camera 1, etc.", file=sys.stderr)
        sys.exit(1)

    # Scroll while keeping one eye closed; brief blinks are ignored
    CLOSED_THRESHOLD = 0.4
    HOLD_FRAMES = 8   # must be closed this many frames to count as "keep closed" (filters blinks)
    SCROLL_EVERY_N_FRAMES = 6  # while keeping closed, scroll every N frames
    SCROLL_AMOUNT = 2  # scroll steps per tick (positive = up, negative = down)

    print("Facial Gesture Scroll – keep left eye closed = scroll up, right = scroll down. Blinks do nothing.")
    print("On macOS: enable Accessibility for Terminal/Cursor for scroll to work.")

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

            if left is not None and right is not None:
                left_closed = left > CLOSED_THRESHOLD
                right_closed = right > CLOSED_THRESHOLD

                if left_closed:
                    left_closed_frames += 1
                else:
                    left_closed_frames = 0
                if right_closed:
                    right_closed_frames += 1
                else:
                    right_closed_frames = 0

                # Only scroll when one eye has been closed for a sustained time (not a blink) and the other is open
                if left_closed_frames >= HOLD_FRAMES and not right_closed:
                    # Keep left closed → scroll up (every SCROLL_EVERY_N_FRAMES to avoid flooding)
                    if (left_closed_frames - HOLD_FRAMES) % SCROLL_EVERY_N_FRAMES == 0:
                        try:
                            scroll_ctrl.perform_scroll(0, SCROLL_AMOUNT)
                        except pyautogui.FailSafeException:
                            print("\nFail-safe triggered (mouse in corner). Quitting.")
                            break
                        if recorder is not None:
                            recorder.write_frame(
                                scroll_dx=0, scroll_dy=SCROLL_AMOUNT,
                                nose_dx=0, nose_dy=0,
                                nose_x=result.nose_x, nose_y=result.nose_y,
                                face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                            )
                elif right_closed_frames >= HOLD_FRAMES and not left_closed:
                    # Keep right closed → scroll down
                    if (right_closed_frames - HOLD_FRAMES) % SCROLL_EVERY_N_FRAMES == 0:
                        try:
                            scroll_ctrl.perform_scroll(0, -SCROLL_AMOUNT)
                        except pyautogui.FailSafeException:
                            print("\nFail-safe triggered (mouse in corner). Quitting.")
                            break
                        if recorder is not None:
                            recorder.write_frame(
                                scroll_dx=0, scroll_dy=-SCROLL_AMOUNT,
                                nose_dx=0, nose_dy=0,
                                nose_x=result.nose_x, nose_y=result.nose_y,
                                face_center_x=result.face_center_x, face_center_y=result.face_center_y,
                            )
                # Both closed or brief closure (blink) → do nothing

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
