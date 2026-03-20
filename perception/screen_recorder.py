"""
Screen Recorder — captures agent actions to video using OpenCV + mss.
Supports recording, pause/resume, and replay.

Recording produces MP4 video at configurable FPS.
Replay overlays recorded mouse clicks on the video for review.

Dependencies: opencv-python, mss, Pillow
Optional: pyautogui (for replay click simulation)
"""

from __future__ import annotations
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import mss
import mss.tools
from PIL import Image


@dataclass
class ClickEvent:
    timestamp: float
    x: int
    y: int
    button: str = "left"
    label: str = ""


@dataclass
class Recording:
    id: str
    start_time: float
    end_time: Optional[float]
    video_path: str
    events_path: str
    monitor: int
    fps: int
    width: int
    height: int
    click_events: list[ClickEvent] = field(default_factory=list)
    duration_seconds: float = 0.0


class ScreenRecorder:
    """
    Record the screen to an MP4 video file.
    Thread-safe: call start/stop from any thread.
    """

    def __init__(
        self,
        output_dir: str = "data/recordings",
        fps: int = 10,
        monitor: int = 1,
    ):
        self._output_dir = Path(output_dir)
        self._fps = fps
        self._monitor = monitor
        self._recording: Optional[Recording] = None
        self._writer = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._paused = False
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, label: str = "") -> str:
        """Start recording. Returns recording ID."""
        if self.is_recording:
            return self._recording.id if self._recording else ""

        rec_id = datetime.now().strftime("rec_%Y%m%d_%H%M%S")
        if label:
            rec_id += f"_{label.replace(' ', '_')[:20]}"

        video_path = str(self._output_dir / f"{rec_id}.mp4")
        events_path = str(self._output_dir / f"{rec_id}_events.json")

        # Get monitor dimensions
        with mss.mss() as sct:
            monitors = sct.monitors
            mon_idx = self._monitor if self._monitor < len(monitors) else 1
            mon = monitors[mon_idx]
            w, h = mon["width"], mon["height"]

        self._recording = Recording(
            id=rec_id,
            start_time=time.time(),
            end_time=None,
            video_path=video_path,
            events_path=events_path,
            monitor=self._monitor,
            fps=self._fps,
            width=w,
            height=h,
        )

        self._stop_event.clear()
        self._paused = False
        self._thread = threading.Thread(
            target=self._record_loop,
            args=(video_path, w, h),
            daemon=True,
        )
        self._thread.start()
        return rec_id

    def stop(self) -> Optional[Recording]:
        """Stop recording and finalize the video file."""
        if not self.is_recording:
            return None
        self._stop_event.set()
        self._thread.join(timeout=10)
        self._thread = None

        if self._recording:
            self._recording.end_time = time.time()
            self._recording.duration_seconds = (
                self._recording.end_time - self._recording.start_time
            )
            # Save events
            events_data = [asdict(e) for e in self._recording.click_events]
            Path(self._recording.events_path).write_text(
                json.dumps(events_data, indent=2), encoding="utf-8"
            )
            return self._recording
        return None

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def record_click(self, x: int, y: int, button: str = "left", label: str = "") -> None:
        """Log a click event with timestamp (call from agent after each click)."""
        if self._recording and self.is_recording:
            self._recording.click_events.append(ClickEvent(
                timestamp=time.time() - self._recording.start_time,
                x=x, y=y, button=button, label=label
            ))

    def _record_loop(self, video_path: str, width: int, height: int) -> None:
        try:
            import cv2
            import numpy as np
        except ImportError:
            # Fallback: save frames as individual PNGs (no video)
            self._record_frames_fallback(video_path)
            return

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_path, fourcc, self._fps, (width, height))

        interval = 1.0 / self._fps

        with mss.mss() as sct:
            monitors = sct.monitors
            mon_idx = self._monitor if self._monitor < len(monitors) else 1
            mon = monitors[mon_idx]

            while not self._stop_event.is_set():
                t0 = time.time()
                if not self._paused:
                    raw = sct.grab(mon)
                    # Convert BGRA → BGR for OpenCV
                    frame = np.frombuffer(raw.bgra, dtype=np.uint8)
                    frame = frame.reshape((raw.height, raw.width, 4))[:, :, :3]
                    # Resize if needed
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv2.resize(frame, (width, height))
                    writer.write(frame)

                elapsed = time.time() - t0
                sleep_for = interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

        writer.release()

    def _record_frames_fallback(self, video_path: str) -> None:
        """Save frames as PNG files when OpenCV is not available."""
        frames_dir = Path(video_path).with_suffix("_frames")
        frames_dir.mkdir(exist_ok=True)
        interval = 1.0 / self._fps
        frame_num = 0

        with mss.mss() as sct:
            monitors = sct.monitors
            mon_idx = self._monitor if self._monitor < len(monitors) else 1
            mon = monitors[mon_idx]

            while not self._stop_event.is_set():
                t0 = time.time()
                if not self._paused:
                    raw = sct.grab(mon)
                    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                    img.save(frames_dir / f"frame_{frame_num:06d}.png")
                    frame_num += 1
                elapsed = time.time() - t0
                sleep_for = interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

    def list_recordings(self) -> list[dict]:
        """List all recordings in the output directory."""
        recordings = []
        for mp4 in self._output_dir.glob("rec_*.mp4"):
            events_file = mp4.with_suffix("").parent / (mp4.stem + "_events.json")
            events = []
            if events_file.exists():
                try:
                    events = json.loads(events_file.read_text())
                except Exception:
                    pass
            stat = mp4.stat()
            recordings.append({
                "id": mp4.stem,
                "path": str(mp4),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "click_count": len(events),
            })
        return sorted(recordings, key=lambda r: r["created"], reverse=True)


class RecordingReplayer:
    """
    Replay a recorded session by simulating mouse movements and clicks.
    Uses pyautogui for replay. Does NOT perfectly reproduce keyboard input.
    """

    def replay(self, recording_id: str, output_dir: str = "data/recordings",
               speed: float = 1.0) -> str:
        """
        Replay a recording. speed=2.0 means 2x faster.
        Returns status message.
        """
        events_path = Path(output_dir) / f"{recording_id}_events.json"
        if not events_path.exists():
            return f"No events file found for recording {recording_id}"

        events = json.loads(events_path.read_text())
        if not events:
            return "No click events to replay"

        try:
            import pyautogui
        except ImportError:
            return "pyautogui not installed — cannot replay clicks"

        pyautogui.FAILSAFE = True
        last_ts = 0.0

        for event in events:
            ts = event["timestamp"]
            delay = (ts - last_ts) / speed
            if delay > 0:
                time.sleep(min(delay, 5.0))  # cap single delay at 5s
            last_ts = ts

            x, y = event["x"], event["y"]
            button = event.get("button", "left")
            pyautogui.click(x, y, button=button)

        return f"Replayed {len(events)} click events from recording {recording_id}"

    def extract_frames(self, video_path: str, output_dir: str, every_n: int = 10) -> list[str]:
        """Extract every Nth frame from a video as PNG files."""
        try:
            import cv2
        except ImportError:
            return []

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        frames = []
        frame_num = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_num % every_n == 0:
                out_path = out_dir / f"frame_{frame_num:06d}.png"
                cv2.imwrite(str(out_path), frame)
                frames.append(str(out_path))
            frame_num += 1

        cap.release()
        return frames
