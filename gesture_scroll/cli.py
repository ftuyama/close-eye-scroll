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

    print("Facial Gesture Scroll – use head movement to scroll. Press 'q' in preview to quit.")
    print("On macOS: enable Accessibility for Terminal/Cursor for scroll to work.")
    print("Options: sensitivity={}, dead_zone={}".format(cfg["sensitivity"], cfg["dead_zone"]))

    show_preview = not args.no_preview
    detector = None
    try:
        detector = FaceMeshDetector()
        prev_nose_x: float | None = None
        prev_nose_y: float | None = None

        for ret, frame in frames(cap):
            if not ret or frame is None:
                break

            result = detector.process(frame)
            nose_x, nose_y = result.nose_x, result.nose_y

            if nose_x is not None and nose_y is not None:
                if prev_nose_x is not None and prev_nose_y is not None:
                    dx = nose_x - prev_nose_x
                    dy = nose_y - prev_nose_y
                    scroll_x, scroll_y = scroll_ctrl.update(dx, dy)
                    try:
                        scroll_ctrl.perform_scroll(scroll_x, scroll_y)
                    except pyautogui.FailSafeException:
                        print("\nFail-safe triggered (mouse in corner). Quitting.")
                        break
                    if recorder is not None:
                        recorder.write_frame(
                            scroll_dx=scroll_x,
                            scroll_dy=scroll_y,
                            nose_dx=dx,
                            nose_dy=dy,
                            nose_x=nose_x,
                            nose_y=nose_y,
                            face_center_x=result.face_center_x,
                            face_center_y=result.face_center_y,
                        )
                prev_nose_x, prev_nose_y = nose_x, nose_y
            else:
                prev_nose_x = prev_nose_y = None

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
