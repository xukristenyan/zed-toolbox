from dataclasses import dataclass, field


VALID_STREAMS = {"left", "right", "depth"}
VALID_DISPLAY_STREAMS = {"left", "right", "depth"}
VALID_RESOLUTIONS = {"HD720", "HD1080", "HD2K", "AUTO"}
VALID_DEPTH_MODES = {"NONE", "PERFORMANCE", "QUALITY", "ULTRA", "NEURAL_LIGHT", "NEURAL", "NEURAL_PLUS"}
VALID_UNITS = {"MILLIMETER", "CENTIMETER", "METER", "INCH", "FOOT"}


@dataclass
class ZedConfig:
    """
    Config for a ZED camera pipeline.

    streams: subset of {"left", "right", "depth"}.
        - "left"  : left RGB image (canonical color view; anchors intrinsics).
        - "right" : right RGB image.
        - "depth" : on-device depth (computed from the stereo pair). Enable
                    this when running ZED standalone, without FFS.

    resolution: ZED SDK resolution preset.

    depth_mode: Default "NEURAL" when "depth" is in streams; auto-coerced to
        "NONE" otherwise. One of
        {"NONE", "PERFORMANCE", "QUALITY", "ULTRA", "NEURAL_LIGHT", "NEURAL", "NEURAL_PLUS"}.

    coordinate_units: distance units for depth values.

    auto_exposure: True -> AEC/AGC enabled; False -> manual exposure + gain.
    exposure: manual exposure value in [0, 100]. Ignored if auto_exposure.
    gain:     manual gain value in [0, 100]. Ignored if auto_exposure.
    """
    streams: list[str] = field(default_factory=lambda: ["left", "right"])

    fps: int = 30
    resolution: str = "HD720"
    depth_mode: str = "NEURAL"
    coordinate_units: str = "METER"

    auto_exposure: bool = False
    exposure: int = 65
    gain: int = 60

    def __post_init__(self):
        if not self.streams:
            raise ValueError("streams must contain at least one entry")
        invalid = set(self.streams) - VALID_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_STREAMS)}"
            )
        if self.resolution not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Unknown resolution {self.resolution!r}. "
                f"Allowed: {sorted(VALID_RESOLUTIONS)}"
            )
        if self.depth_mode not in VALID_DEPTH_MODES:
            raise ValueError(
                f"Unknown depth_mode {self.depth_mode!r}. "
                f"Allowed: {sorted(VALID_DEPTH_MODES)}"
            )
        if self.coordinate_units not in VALID_UNITS:
            raise ValueError(
                f"Unknown coordinate_units {self.coordinate_units!r}. "
                f"Allowed: {sorted(VALID_UNITS)}"
            )
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if not (0 <= self.exposure <= 100):
            raise ValueError("exposure must be in [0, 100]")
        if not (0 <= self.gain <= 100):
            raise ValueError("gain must be in [0, 100]")

        if "depth" not in self.streams:
            self.depth_mode = "NONE"


@dataclass
class ViewerConfig:
    """
    Config for the Viewer (display window).

    show: subset of {"left", "right", "depth"}.
        Streams listed here but not present in the camera's output are
        silently skipped. Overlays (if provided) are applied to the "left"
        panel only.
    fps: display rate cap; the capture thread runs faster, the viewer
        rate-limits its imshow calls to this rate.
    """
    show: list[str] = field(default_factory=lambda: ["left"])
    fps: int = 30

    def __post_init__(self):
        if not self.show:
            raise ValueError("show must contain at least one stream id")
        invalid = set(self.show) - VALID_DISPLAY_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown display stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_DISPLAY_STREAMS)}"
            )
        if self.fps <= 0:
            raise ValueError("fps must be positive")


@dataclass
class RecorderConfig:
    """
    Config for the Recorder (per-camera).

    streams: subset of {"left", "right", "depth"}.
        Behavior per stream:
        - "left":  always saved as .mp4 (lossy, visual).
                   Additionally saved as .npz (lossless) when "right" is also enabled.
        - "right": saved as .npz (lossless), plus a calibration.json containing
                   intrinsics, baseline, and capture metadata for offline replay
                   (e.g. Fast-FoundationStereo).
        - "depth": saved as .mp4 colormap (lossy, visual review only).

    Files saved under {save_dir}/{save_name}/:
        cam_<last3>_left.mp4          (when "left" in streams)
        cam_<last3>_left.npz          (when both "left" and "right")
        cam_<last3>_right.npz         (when "right" in streams)
        cam_<last3>_depth.mp4         (when "depth" in streams)
        cam_<last3>_overlay.mp4       (when save_with_overlays and "left")
        cam_<last3>_calibration.json  (when "right" in streams)

    save_name: if None, auto-set to a timestamp at start() (e.g. "20260511_153023").
    fps: rate at which frames are sampled from the camera. Default 10 Hz. Up to 30 Hz.
    """
    streams: list[str] = field(default_factory=lambda: ["left"])
    save_dir: str = "./recordings"
    save_name: str | None = None
    fps: int = 10
    save_with_overlays: bool = False

    def __post_init__(self):
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if not self.streams:
            raise ValueError("streams must contain at least one entry")
        invalid = set(self.streams) - VALID_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_STREAMS)}"
            )


@dataclass
class CameraConfig:
    """
    Top-level config for a Camera (ZedCamera + optional Viewer + optional Recorder).

    Sub-configs may be passed as dataclasses or dicts (normalized in __post_init__).
    Setting viewer=None or recorder=None disables that component.
    """
    zed: ZedConfig | dict = field(default_factory=ZedConfig)
    viewer: ViewerConfig | dict | None = None
    recorder: RecorderConfig | dict | None = None

    def __post_init__(self):
        if isinstance(self.zed, dict):
            self.zed = ZedConfig(**self.zed)
        if isinstance(self.viewer, dict):
            self.viewer = ViewerConfig(**self.viewer)
        if isinstance(self.recorder, dict):
            self.recorder = RecorderConfig(**self.recorder)
