# Close Eye Scroll

Scroll with your eyes: **left eye closed** = scroll up, **right eye closed** = scroll down. Uses the webcam, MediaPipe Face Landmarker, and PyAutoGUI.

- Scroll only activates when you’re **looking straight** at the camera (nose in zone, head pitch within range).
- **Blinks are ignored**: the other eye must stay open for the last `hold_frames` frames.
- Preview shows a red “look straight” zone, debug variables, and status (e.g. `SCROLL UP`, `SKIP: Blink`).

## Requirements

- Python 3.10+
- Webcam
- **macOS**: grant **Camera** and **Accessibility** (Terminal/IDE) in **System Settings → Privacy & Security**.
- On first run the face model (~10 MB) is downloaded.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Or: `python -m gesture_scroll.cli`. Press **q** in the preview to quit.

## Options

| Option | Description |
|--------|-------------|
| `--no-preview` | Disable camera preview. |
| `--camera ID` | Camera device (default `0`). |
| `--closed-threshold FLOAT` | Eye-closed blend 0–1 (default from config). |
| `--hold-frames N` | Frames eye must stay closed before scroll. |
| `--scroll-amount N` | Scroll steps per tick. |
| `--record FILE` | Record scroll events to CSV. |
| `--record-landmarks` | Include nose/face coordinates in recording. |
| `--save-config` | Write current options to `config.json` and exit. |

## Configuration

`config.json` (merge with defaults):

| Key | Description |
|-----|-------------|
| `closed_threshold` | Blend above which eye counts as closed. |
| `hold_frames` | Frames closed before scroll starts (filters blinks). |
| `scroll_every_n_frames` | Scroll every N frames while held. |
| `scroll_amount` | Scroll steps per tick. |
| `look_straight_nose_x_min` / `_max` | Nose X range (0–1) for “looking straight”. |
| `look_straight_nose_y_min` / `_max` | Nose Y range (0–1). |
| `look_straight_max_head_pitch_deg` | Max head tilt (degrees); avoids scroll when looking down/up. |

## Troubleshooting

- **No scroll** – Add Terminal/IDE to **Accessibility**. Ensure face is in the red zone and you’re not looking down.
- **Fontconfig/matplotlib** – `export MPLCONFIGDIR=$PWD/.mplcache`
- **No face** – Check lighting; try `--camera 1`.
- **Fail-safe** – PyAutoGUI exits when the cursor is in a screen corner; move it or press **q**.
