"""Record gesture data (deltas and/or landmarks) to CSV for calibration/debug."""
from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any


class GestureRecorder:
    """Append timestamp, scroll deltas, and optional landmark coords to a CSV file."""

    def __init__(self, filepath: Path | str, record_landmarks: bool = False):
        self._path = Path(filepath)
        self._record_landmarks = record_landmarks
        self._file: Any = None
        self._writer: csv.writer | None = None
        self._open = False

    def start(self) -> None:
        """Open file and write header."""
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        header = ["timestamp_sec", "scroll_dx", "scroll_dy", "nose_dx", "nose_dy"]
        if self._record_landmarks:
            header.extend(["nose_x", "nose_y", "face_center_x", "face_center_y"])
        self._writer.writerow(header)
        self._open = True

    def write_frame(
        self,
        scroll_dx: float,
        scroll_dy: float,
        nose_dx: float,
        nose_dy: float,
        nose_x: float | None = None,
        nose_y: float | None = None,
        face_center_x: float | None = None,
        face_center_y: float | None = None,
    ) -> None:
        """Append one row. Landmark fields only used when record_landmarks is True."""
        if not self._open or self._writer is None:
            return
        row = [time.perf_counter(), scroll_dx, scroll_dy, nose_dx, nose_dy]
        if self._record_landmarks:
            row.extend(
                [
                    nose_x if nose_x is not None else "",
                    nose_y if nose_y is not None else "",
                    face_center_x if face_center_x is not None else "",
                    face_center_y if face_center_y is not None else "",
                ]
            )
        self._writer.writerow(row)

    def stop(self) -> None:
        """Close the file."""
        if self._file is not None:
            self._file.close()
            self._file = None
        self._writer = None
        self._open = False

    def __enter__(self) -> "GestureRecorder":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
