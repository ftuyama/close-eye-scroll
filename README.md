# Facial Gesture Scroll

Scroll with your eyes using the webcam: **keep your left eye closed** = scroll up, **keep your right eye closed** = scroll down. Brief blinks are ignored; only sustained eye closure triggers scrolling. Uses MediaPipe Face Landmarker (blendshapes) and PyAutoGUI.

## Requirements

- Python 3.10+
- Webcam
- **macOS**: Terminal (or the app running the script) must have **Camera** and **Accessibility** permissions.  
  **System Settings → Privacy & Security → Camera** and **Accessibility** → add Terminal (or Cursor/your IDE).
- On first run, the face landmarker model (~10 MB) is downloaded automatically to the project folder.

## Setup

1. Create and activate the virtual environment (use the Python from your terminal):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run:

   ```bash
   python run.py
   ```

   Or as a module:

   ```bash
   python -m gesture_scroll.cli
   ```

A preview window shows the camera and face landmarks. **Keep your left eye closed** to scroll up, **keep your right eye closed** to scroll down; brief blinks do nothing. Press **q** in the preview window to quit.

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
| `--save-config` | Save current CLI options to `config.json` and exit. |

Examples:

```bash
# Higher sensitivity, no preview
python run.py --sensitivity 2.0 --no-preview

# Record gestures to CSV (with landmark coordinates)
python run.py --record gestures.csv --record-landmarks

# Save your preferred options to config
python run.py --sensitivity 1.5 --dead-zone 0.03 --save-config
```

## Configuration file

Default settings are in `config.json` (created when you use `--save-config`). You can edit it to set:

- `sensitivity`, `dead_zone`, `scroll_scale`, `max_scroll_per_frame`
- `smoothing_alpha` (lower = smoother, less responsive)
- `scroll_vertical`, `scroll_horizontal`, `invert_vertical`, `invert_horizontal`

## Troubleshooting

- **Scroll does nothing on macOS**  
  Add Terminal (or Cursor) to **System Settings → Privacy & Security → Accessibility** and restart the app.

- **Fontconfig / matplotlib cache errors**  
  Set a writable cache directory before running, e.g.:  
  `export MPLCONFIGDIR=$PWD/.mplcache`

- **No face detected**  
  Ensure good lighting and the camera can see your face. Try adjusting `--camera` if you have multiple cameras.

- **"Fail-safe triggered" / app quits**  
  PyAutoGUI stops the app when the mouse is in a screen corner (safety feature). Move the cursor away from the corners to avoid this, or press **q** in the preview to quit normally.
