# ZED Toolbox

A small Python toolbox for streaming, viewing, and recording from Stereolabs ZED stereo cameras. Built around composable, typed configs; supports synchronized multi-camera setups and Fast-FoundationStereo-replay-friendly recording (lossless left+right stereo pair + calibration).

## Installation

Requires Python 3.10. The ZED SDK and its Python bindings (`pyzed`) are required system-level dependencies.

### 1. Install the ZED SDK + build the `pyzed` wheel

1. Download the SDK from the [Stereolabs releases page](https://www.stereolabs.com/developers/release/) for your platform.
2. Install it following the [Linux SDK guide](https://www.stereolabs.com/docs/development/zed-sdk/linux).
3. Build the Python wheel:

    ```bash
    cd /usr/local/zed
    python get_python_api.py
    ```

    The wheel will be written to `/usr/local/zed/pyzed-<sdk-version>-cp310-cp310-linux_x86_64.whl`. Update `pyproject.toml`'s `[tool.uv.sources]` entry if the path differs.

### 2. Install this repo

```bash
git clone https://github.com/xukristenyan/zed-toolbox.git
cd zed-toolbox
uv sync
```

Or as an editable dependency in another project:

```bash
# uv
uv add --editable /path/to/zed-toolbox

# pip
pip install -e /path/to/zed-toolbox
```

## Quick start

```python
from zed_toolbox import (
    Camera, CameraConfig, ZedConfig, ViewerConfig, KeyListener,
)

cam = Camera(24944966, CameraConfig(
    zed=ZedConfig(streams=["left", "right"]),
    viewer=ViewerConfig(show=["left"]),
))

cam.launch()
try:
    with KeyListener() as keys:
        while cam.is_alive:
            cam.get_observations()
            if keys.consume_pressed("esc"):
                break
finally:
    cam.shutdown()
```

To find your camera's serial number, run `uv run scripts/get_serial.py`. More patterns in `scripts/`.

## Architecture

| Class | Role |
|---|---|
| `ZedCamera` | Direct `pyzed` wrapper. Captures frames in a background thread; exposes them as numpy arrays via `get_current_state()`. |
| `Viewer` | Display sink. Accepts a streams dict and renders selected streams side-by-side in one OpenCV window. |
| `Recorder` | File sink. Accepts a streams dict; writes per-stream files (mp4 or npz) plus calibration when applicable. |
| `Camera` | Single-camera orchestrator. Composes `ZedCamera` + optional `Viewer` + optional `Recorder`. Exposes `get_observations()`, `start_recording()`, `stop_recording()`. |
| `CameraSystem` | Multi-camera coordinator. Broadcasts the same orchestration across N cameras. |
| `KeyListener` | Terminal-stdin keyboard reader (utils). Edge-triggered; consume each press once. |

The orchestrator is a pure facade — no keyboard polling, no auto-recording. The caller drives the loop.

## Configuration

Four dataclasses. Each accepts a dict alternative (the constructor normalizes dicts → dataclasses).

### `ZedConfig` — camera capture

```python
@dataclass
class ZedConfig:
    streams: list[str] = ["left", "right"]       # subset of {"left", "right", "depth"}
    fps: int = 30
    resolution: str = "HD720"                    # one of {"HD720", "HD1080", "HD2K", "AUTO"}
    depth_mode: str = "NEURAL"                   # auto-coerced to "NONE" if "depth" not in streams
    coordinate_units: str = "METER"
    auto_exposure: bool = False
    exposure: int = 65                           # [0, 100]; ignored if auto_exposure
    gain: int = 60                               # [0, 100]; ignored if auto_exposure
```

Stream IDs:
- `"left"` — left RGB image (BGR). Canonical color view; anchors intrinsics.
- `"right"` — right RGB image (BGR). Enable alongside `"left"` for external stereo (e.g. Fast-FoundationStereo).
- `"depth"` — on-device depth (float, in `coordinate_units`). Enable for ZED-standalone use without FFS.

Depth modes (`"NONE"`, `"PERFORMANCE"`, `"QUALITY"`, `"ULTRA"`, `"NEURAL_LIGHT"`, `"NEURAL"`, `"NEURAL_PLUS"`):
classical modes (`PERFORMANCE/QUALITY/ULTRA`) are deprecated in SDK 5.x but still functional. `NEURAL*` modes require the SDK's AI module (TRT-optimized model files).

ZED resolutions are fixed presets — width/height are not independently configurable.

### `ViewerConfig` — display window

```python
@dataclass
class ViewerConfig:
    show: list[str] = ["left"]                   # subset of {"left", "right", "depth"}
    fps: int = 30                                # display rate cap
```

Overlays (when provided) are drawn on the `"left"` panel only.

### `RecorderConfig` — file output

```python
@dataclass
class RecorderConfig:
    streams: list[str] = ["left"]                # subset of {"left", "right", "depth"}
    save_dir: str = "./recordings"
    save_name: str | None = None                 # None = auto-timestamp at start()
    fps: int = 10                                # frames sampled per second (decoupled from camera fps)
    save_with_overlays: bool = False
```

### `CameraConfig` — top-level

```python
@dataclass
class CameraConfig:
    zed: ZedConfig | dict = ZedConfig()
    viewer: ViewerConfig | dict | None = None       # None disables the viewer
    recorder: RecorderConfig | dict | None = None     # None disables the recorder
```

## Examples

| File | Use case |
|---|---|
| `scripts/stream_only.py` | Direct `ZedCamera`. Saves N frames; prints intrinsics + baseline; SSH-friendly. |
| `scripts/view_live.py` | `Camera` + `Viewer`. Live display; ESC to quit. |
| `scripts/record_headless.py` | `Camera` + `Recorder`. KeyListener-driven start/stop; no viewer. |
| `scripts/view_and_record.py` | All three. Live display + on-demand recording. |
| `scripts/record_for_ffs.py` | Stereo pair capture for offline FoundationStereo replay. |
| `scripts/multi_camera.py` | `CameraSystem` with synchronized recording across two cameras. |
| `scripts/get_serial.py` | Print the serial number of the connected ZED. |

Run any of them with `uv run scripts/<name>.py`.

## Recording outputs

Files saved under `{save_dir}/{save_name}/`. Names always carry a `cam_<last3-of-serial>_` prefix so multiple cameras don't collide.

| File | Created when |
|---|---|
| `cam_<last3>_left.mp4` | `"left"` in streams (lossy h264, ~5 MB/min @ 10 fps) |
| `cam_<last3>_left.npz` | `"left"` AND `"right"` in streams (lossless uint8 BGR, ~250 MB/min @ 10 fps at HD720) |
| `cam_<last3>_right.npz` | `"right"` in streams (lossless uint8 BGR) |
| `cam_<last3>_depth.mp4` | `"depth"` in streams (lossy colormap, visual review only) |
| `cam_<last3>_overlay.mp4` | `save_with_overlays=True` and `"left"` in streams |
| `cam_<last3>_calibration.json` | `"right"` in streams |

### Why left gets two formats when right is enabled

Recording the stereo pair signals an intent to preserve data for offline use (FFS replay, SAM2 on color, photometric analysis, etc.). The Recorder upgrades the left stream to bit-exact `.npz` while still writing `.mp4` for quick visual review. ~10× larger than mp4-only, but no compression artifacts.

### `cam_<last3>_calibration.json` fields

```json
{
    "K": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
    "baseline": 0.120130,
    "streams": ["left", "right"],
    "depth_mode": "NONE",
    "coordinate_units": "METER",
    "resolution": "HD720",
    "camera_fps": 30,
    "recorder_fps": 10
}
```

`K` is anchored to the rectified left camera (the SDK delivers rectified pairs by default, so left and right share the same K — one matrix is sufficient). `baseline` is the stereo baseline in `coordinate_units`.

## Offline Fast-FoundationStereo replay

After recording with `streams=["left", "right"]`, the saved files are self-contained for offline depth re-inference:

```python
import numpy as np, json
from your_ffs_client import FFSClient

session = "recordings/ffs_trial"
calib = json.load(open(f"{session}/cam_966_calibration.json"))
left  = np.load(f"{session}/cam_966_left.npz")["frames"]
right = np.load(f"{session}/cam_966_right.npz")["frames"]

client = FFSClient()
client.set_intrinsics(np.array(calib["K"]), calib["baseline"])

for i in range(len(left)):
    out = client.infer(left[i], right[i], returns=("depth",))
    depth = out["depth"]
    # ...
```

The stereo images are bit-exact to capture, so the result is identical to running FFS live during recording.

## Overlays

`Camera.get_observations(overlays=...)` and `Viewer.update`/`Recorder.update` accept an optional list of overlay dicts. Overlays are drawn on the **left** panel only.

```python
overlays = [
    {"type": "dot",  "xy": (640, 360), "radius": 6, "color": (0, 255, 0)},
    {"type": "text", "content": "trial_42", "position": (50, 50), "color": (0, 0, 255)},
]
cam.get_observations(overlays=overlays)
```

## Notes

- **ZED depth vs FFS.** As of SDK 5.x, ZED's on-device depth is neural by default (`NEURAL` / `NEURAL_PLUS`); classical modes are deprecated. For most scene depth the on-device output is competitive with FoundationStereo. For fine objects, reflective/textureless surfaces, or anything grasp-critical, FFS still tends to pull ahead — record `streams=["left", "right"]` and run FFS offline (see above).
- **NEURAL modes require TRT.** The ZED AI module ships TensorRT-optimized depth models. If you see `NEURAL TRT NOT FOUND` at launch, your SDK install is missing them — either reinstall or run the SDK's AI-model download tool. Classical modes (`PERFORMANCE`/`QUALITY`/`ULTRA`) still work without TRT.
- **Memory cost during recording.** npz streams (left+right in FFS mode) are buffered in RAM until `stop_recording()` flushes them. Roughly 200–500 MB per minute for the stereo pair at 10 fps at HD720. Long sessions can pressure RAM — split into multiple shorter recordings if needed.