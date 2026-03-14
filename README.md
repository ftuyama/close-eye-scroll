# Facial Gesture Scroll

Scroll with your eyes using the webcam: **keep your left eye closed** = scroll up, **keep your right eye closed** = scroll down. Brief blinks are ignored. Uses MediaPipe Face Landmarker and PyAutoGUI.

## Requirements

- Python 3.10+
- Webcam
- **macOS**: **Camera** and **Accessibility** for Terminal (or your IDE):
  **System Settings → Privacy & Security → Camera** and **Accessibility**
- On first run, the face landmarker model (~10 MB) is downloaded to the project folder.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Or: `python -m gesture_scroll.cli`

A preview window shows the camera and face landmarks. **Keep your left eye closed** to scroll up, **keep your right eye closed** to scroll down; brief blinks do nothing. Press **q** to quit.

## Options

| Option | Description |
|--------|-------------|
| `--sensitivity FLOAT` | Scroll sensitivity (e.g. `0.5`–`3.0`). Default from config. |
| `--dead-zone FLOAT` | Minimum movement before scrolling (normalized, e.g. `0.02`). |
| `--no-preview` | Disable camera preview (headless). |
| `--record FILE` | Record gesture data (scroll deltas) to a CSV file. |
| `--record-landmarks` | When using `--record`, also save nose/face landmark coordinates. |
| `--scroll-vertical` / `--no-scroll-vertical` | Enable or disable vertical scroll. |
| `--scroll-horizontal` | Enable horizontal scroll. |
| `--invert-vertical` / `--invert-horizontal` | Invert scroll direction. |
| `--camera ID` | Camera device ID (default `0`). |
| `--closed-threshold FLOAT` | Eye-closed blend threshold 0–1 (default `0.4`). |
| `--hold-frames N` | Frames eye must stay closed before scrolling (default `8`). |
| `--scroll-amount N` | Scroll steps per tick (default `2`). |
| `--save-config` | Save current options to `config.json` and exit. |

## Configuration

`config.json` (created with `--save-config` or by hand) can set:

- `closed_threshold` – blend value above which eye is “closed”
- `hold_frames` – frames closed before scroll starts, to ignore blinks
- `scroll_every_n_frames` – scroll every N frames while eye stays closed
- `scroll_amount` – scroll steps per tick

## Troubleshooting

- **Scroll does nothing** – Add Terminal (or your IDE) to **Accessibility** in System Settings.
- **Fontconfig / matplotlib errors** – `export MPLCONFIGDIR=$PWD/.mplcache`
- **No face detected** – Check lighting and try `--camera 1`.
- **“Fail-safe triggered”** – PyAutoGUI quits when the mouse is in a corner; move the cursor or press **q** to quit normally.
