import json
import time
from pathlib import Path

import cv2
import numpy as np

from .config import RecorderConfig
from .utils import draw_overlays


class Recorder:
    """
    Records selected streams from a ZED camera. Explicit start() / stop().

    Behavior follows cfg.streams (same vocabulary as ZedConfig.streams):
        - "left":  left.mp4 always; left.npz also if "right" is enabled.
        - "right": right.npz + calibration.json.
        - "depth": depth.mp4 (lossy colormap, visual only).

    npz streams are buffered in memory during recording and saved at stop().
    Memory cost: at 1280x720 color, ~5–8 MB per second of stereo pair at 10 fps
    after compression; budget for your expected session length.
    """

    def __init__(self, serial, config=None):
        self.serial = serial

        if config is None:
            config = RecorderConfig()
        elif isinstance(config, dict):
            config = RecorderConfig(**config)
        self.cfg = config

        self._wants_left = "left" in self.cfg.streams
        self._wants_right = "right" in self.cfg.streams
        self._wants_depth = "depth" in self.cfg.streams
        self._save_left_npz = self._wants_left and self._wants_right

        self.frame_interval = 1.0 / self.cfg.fps if self.cfg.fps > 0 else 0
        self._last_update = 0
        self._is_recording = False
        self.session_dir = None

        self._left_mp4 = None
        self._depth_mp4 = None
        self._overlay_mp4 = None
        self._left_buf = None
        self._right_buf = None


    def start(self, calibration=None):
        """Open the session directory; write calibration.json if applicable.

        calibration: optional dict with keys 'intrinsics', 'streams',
            'depth_mode', 'coordinate_units', 'resolution', 'camera_fps'.
            Written to calibration.json when "right" is in cfg.streams.
        """
        if self._is_recording:
            return

        save_name = self.cfg.save_name or time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(self.cfg.save_dir) / save_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if self._wants_right:
            if calibration:
                self._write_calibration(calibration)
            else:
                print(f"[Recorder {str(self.serial)[-3:]}] WARNING: right-stream "
                      f"recording started without calibration; recordings will not "
                      f"be self-contained for FFS replay.")

        if self._save_left_npz:
            self._left_buf = []
        if self._wants_right:
            self._right_buf = []

        self._last_update = 0
        self._is_recording = True
        print(f"[Recorder {str(self.serial)[-3:]}] start -> {self.session_dir}")


    def update(self, streams, overlays=None):
        if not self._is_recording:
            return
        now = time.time()
        if now - self._last_update < self.frame_interval:
            return
        self._last_update = now

        if self._wants_left:
            left = streams.get("left")
            if left is not None:
                self._maybe_init_left_mp4(left)
                self._left_mp4.write(left)
                if self._save_left_npz:
                    self._left_buf.append(left.copy())
                if self.cfg.save_with_overlays:
                    self._maybe_init_overlay_mp4(left)
                    img = draw_overlays(left, overlays) if overlays else left
                    self._overlay_mp4.write(img)

        if self._wants_right:
            right = streams.get("right")
            if right is not None:
                self._right_buf.append(right.copy())

        if self._wants_depth:
            depth = streams.get("depth")
            if depth is not None:
                self._maybe_init_depth_mp4(depth)
                self._depth_mp4.write(self._depth_to_color(depth))


    def stop(self):
        if not self._is_recording:
            return
        self._is_recording = False

        if self._left_mp4 is not None:
            self._left_mp4.release()
            self._left_mp4 = None
        if self._depth_mp4 is not None:
            self._depth_mp4.release()
            self._depth_mp4 = None
        if self._overlay_mp4 is not None:
            self._overlay_mp4.release()
            self._overlay_mp4 = None

        if self._save_left_npz and self._left_buf:
            arr = np.stack(self._left_buf, axis=0)
            np.savez_compressed(self._npz_path("left"), frames=arr)
        if self._wants_right and self._right_buf:
            arr = np.stack(self._right_buf, axis=0)
            np.savez_compressed(self._npz_path("right"), frames=arr)

        self._left_buf = None
        self._right_buf = None

        print(f"[Recorder {str(self.serial)[-3:]}] saved to {self.session_dir}")


    def _maybe_init_left_mp4(self, frame):
        if self._left_mp4 is None:
            h, w = frame.shape[:2]
            self._left_mp4 = self._open_mp4("left", w, h)


    def _maybe_init_depth_mp4(self, frame):
        if self._depth_mp4 is None:
            h, w = frame.shape[:2]
            self._depth_mp4 = self._open_mp4("depth", w, h)


    def _maybe_init_overlay_mp4(self, frame):
        if self._overlay_mp4 is None:
            h, w = frame.shape[:2]
            self._overlay_mp4 = self._open_mp4("overlay", w, h)


    def _open_mp4(self, stream, w, h):
        path = str(self.session_dir / f"cam_{str(self.serial)[-3:]}_{stream}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        return cv2.VideoWriter(path, fourcc, self.cfg.fps, (w, h))


    def _npz_path(self, stream):
        return str(self.session_dir / f"cam_{str(self.serial)[-3:]}_{stream}.npz")


    @staticmethod
    def _depth_to_color(depth, min_depth=0.01, max_depth=3.0):
        clipped = np.clip(depth, min_depth, max_depth)
        normalized = cv2.normalize(clipped, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        normalized[np.isnan(depth)] = 0
        return cv2.applyColorMap(normalized, cv2.COLORMAP_JET)


    def _write_calibration(self, calibration):
        out = {}
        intr = calibration.get("intrinsics") or {}
        if intr.get("matrix") is not None:
            out["K"] = intr["matrix"].tolist()
        if intr.get("baseline") is not None:
            out["baseline"] = float(intr["baseline"])
        for key in ("streams", "depth_mode", "coordinate_units", "resolution", "camera_fps"):
            if key in calibration:
                v = calibration[key]
                out[key] = list(v) if isinstance(v, (list, tuple, set)) else v
        out["recorder_fps"] = self.cfg.fps

        path = self.session_dir / f"cam_{str(self.serial)[-3:]}_calibration.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
