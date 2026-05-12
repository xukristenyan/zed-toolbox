import time
import threading
import numpy as np
import pyzed.sl as sl

from .config import ZedConfig


class ZedCamera:
    """
    Stream from a single ZED stereo camera in a background thread.

    Access images via attributes (left_image, right_image, depth_image —
    only the streams enabled in config are populated) or via
    get_current_state() for a snapshot dict under lock.

    The left camera anchors the canonical intrinsics; depth (when enabled)
    is registered to the left frame.
    """

    def __init__(self, serial, config=None):
        if not serial:
            raise ValueError("Missing camera serial number.")
        self.serial = serial

        if config is None:
            config = ZedConfig()
        elif isinstance(config, dict):
            config = ZedConfig(**config)
        self.cfg = config

        self._has_left = "left" in self.cfg.streams
        self._has_right = "right" in self.cfg.streams
        self._has_depth = "depth" in self.cfg.streams

        self.camera = sl.Camera()
        self.init_params = self._build_init_params()

        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._started = False

        self.left_image = None
        self.right_image = None
        self.depth_image = None

        self.intrinsics = None


    def _build_init_params(self):
        params = sl.InitParameters()
        params.set_from_serial_number(self.serial)
        params.camera_fps = self.cfg.fps
        params.camera_resolution = sl.RESOLUTION[self.cfg.resolution]
        params.depth_mode = sl.DEPTH_MODE[self.cfg.depth_mode]
        params.coordinate_units = sl.UNIT[self.cfg.coordinate_units]
        return params


    def launch(self):
        try:
            err = self.camera.open(self.init_params)
            if err != sl.ERROR_CODE.SUCCESS:
                raise RuntimeError(
                    f"sl.Camera.open() failed with {err}. Check camera connection."
                )
            self._started = True

            if self.cfg.auto_exposure:
                self.camera.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 1)
            else:
                self.camera.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 0)
                self.camera.set_camera_settings(sl.VIDEO_SETTINGS.EXPOSURE, self.cfg.exposure)
                self.camera.set_camera_settings(sl.VIDEO_SETTINGS.GAIN, self.cfg.gain)

            self._capture_intrinsics()

            for _ in range(30):
                self.camera.grab()

            self._thread = threading.Thread(target=self._update_frame, daemon=True)
            self._thread.start()

            print(f"[Zed {str(self.serial)[-3:]}] Launched!")

        except Exception as e:
            print(f"[Zed {str(self.serial)[-3:]}] Failed to launch ({type(e).__name__}: {e})")
            self.shutdown()
            raise


    def _capture_intrinsics(self):
        info = self.camera.get_camera_information()
        calib = info.camera_configuration.calibration_parameters
        left = calib.left_cam

        K = np.array([
            [left.fx, 0,       left.cx],
            [0,       left.fy, left.cy],
            [0,       0,       1],
        ])
        translation = calib.stereo_transform.get_translation().get()
        baseline = float(abs(translation[0]))

        self.intrinsics = {
            "matrix": K,
            "raw": left,
            "baseline": baseline,
        }


    def _update_frame(self):
        left = sl.Mat() if self._has_left else None
        right = sl.Mat() if self._has_right else None
        depth = sl.Mat() if self._has_depth else None

        while not self._stop_event.is_set():
            try:
                if self.camera.grab() != sl.ERROR_CODE.SUCCESS:
                    continue

                if left is not None:
                    self.camera.retrieve_image(left, sl.VIEW.LEFT)
                if right is not None:
                    self.camera.retrieve_image(right, sl.VIEW.RIGHT)
                if depth is not None:
                    self.camera.retrieve_measure(depth, sl.MEASURE.DEPTH)

                with self._lock:
                    if left is not None:
                        self.left_image = np.ascontiguousarray(left.get_data()[:, :, :3])
                    if right is not None:
                        self.right_image = np.ascontiguousarray(right.get_data()[:, :, :3])
                    if depth is not None:
                        self.depth_image = depth.get_data().copy()

            except Exception as e:
                print(f"[Zed {str(self.serial)[-3:]}] Error in capture thread: {e}")
                time.sleep(0.5)


    def get_current_state(self):
        with self._lock:
            imgs = {
                "left": self.left_image,
                "right": self.right_image,
                "depth": self.depth_image,
            }
            return {k: v for k, v in imgs.items() if v is not None}


    def get_intrinsics(self):
        return self.intrinsics


    def deproject_pixel_to_point(self, xy):
        """
        (u, v) pixel -> 3D point in the left-camera frame.

        Returns None if depth is disabled, the pixel is out of bounds, or
        the depth value is invalid. Units match cfg.coordinate_units.
        """
        if not self._has_depth or self.intrinsics is None:
            raise RuntimeError(
                "deproject_pixel_to_point requires the 'depth' stream and a launched camera."
            )
        u, v = int(xy[0]), int(xy[1])

        with self._lock:
            if self.depth_image is None:
                return None
            h, w = self.depth_image.shape[:2]
            if not (0 <= u < w and 0 <= v < h):
                return None
            z = float(self.depth_image[v, u])

        if not np.isfinite(z) or z <= 0:
            return None

        K = self.intrinsics["matrix"]
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy
        return [x, y, z]


    def shutdown(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        if self._started:
            self.camera.close()
            self._started = False
        print(f"[Zed {str(self.serial)[-3:]}] Shutdown complete.")
