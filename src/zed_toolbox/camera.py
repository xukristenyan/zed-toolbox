from .config import CameraConfig
from .zed import ZedCamera
from .viewer import Viewer
from .recorder import Recorder


class Camera:
    """
    High-level facade: ZedCamera + optional Viewer + optional Recorder.

    Pure orchestration — no keyboard input, no recording auto-trigger. The
    caller (or CameraSystem) decides when to start/stop recording.

    Typical use:
        cam = Camera(serial, CameraConfig(
            zed=ZedConfig(streams=["left", "right"]),
            viewer=ViewerConfig(show=["left"]),
        ))
        cam.launch()
        while cam.is_alive:
            streams = cam.get_observations(overlays=...)
        cam.shutdown()
    """

    def __init__(self, serial, config=None):
        self.serial = serial

        if config is None:
            config = CameraConfig()
        elif isinstance(config, dict):
            config = CameraConfig(**config)
        self.cfg = config

        self.zed_camera = ZedCamera(serial, self.cfg.zed)
        self.viewer = Viewer(serial, self.cfg.viewer) if self.cfg.viewer is not None else None
        self.recorder = Recorder(serial, self.cfg.recorder) if self.cfg.recorder is not None else None

        self._is_alive = False


    def launch(self):
        self.zed_camera.launch()
        self._is_alive = True


    def get_observations(self, overlays=None):
        """Return the latest stream snapshot from the camera and, as a side
        effect, push it to the viewer and recorder if they're enabled.

        Call this once per loop iteration. Returns the streams dict
        (matching ZedCamera.get_current_state()).
        """
        streams = self.zed_camera.get_current_state()
        if self.viewer is not None:
            self.viewer.update(streams, overlays=overlays)
        if self.recorder is not None:
            self.recorder.update(streams, overlays=overlays)
        return streams


    def start_recording(self):
        if self.recorder is None:
            return
        zed_cfg = self.zed_camera.cfg
        calibration = {
            "intrinsics": self.zed_camera.intrinsics,
            "streams": list(zed_cfg.streams),
            "depth_mode": zed_cfg.depth_mode,
            "coordinate_units": zed_cfg.coordinate_units,
            "resolution": zed_cfg.resolution,
            "camera_fps": zed_cfg.fps,
        }
        self.recorder.start(calibration=calibration)


    def stop_recording(self):
        if self.recorder is not None:
            self.recorder.stop()


    def shutdown(self):
        if self.recorder is not None:
            self.recorder.stop()
        if self.viewer is not None:
            self.viewer.shutdown()
        self.zed_camera.shutdown()
        self._is_alive = False


    @property
    def is_alive(self):
        return self._is_alive
