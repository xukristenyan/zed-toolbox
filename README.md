# Zed-Toolbox

This is a toolbox for connecting, streaming, visualizing, and recording a Zed camera in robotics research based on Python.

## Installation

### Get `pyzed` API (if you don't have it)
1. Download the SDK from [Zed official website](https://www.stereolabs.com/developers/release/5.1) according to your computer settings.
2. Install the downloaded SDK following this [guide](https://www.stereolabs.com/docs/development/zed-sdk/linux).
3. Build python API:

    ```bash
    conda create -n zed python=3.10 && conda activate
    cd /usr/local/zed
    python get_python_api.py
    ```

Then the wheel is built under `/usr/local/zed/pyzed-5.1-cp310-cp310-linux_x86_64.whl` by default.

### Install this repo and `pyzed` in your project env

```bash
# With HTTP
git clone https://github.com/xukristenyan/realsense-toolbox.git

# With SSH
git clone git@github.com:xukristenyan/realsense-toolbox.git
```

```bash
# using uv
uv add --editable [path/to/zed-toolbox]     # remember to update the pyproject.toml file with the correct wheel path
# or
uv sync
```

## Usage

### Examples for Different Needs
The toolbox is organized into a clear hierarchy of classes, where each level abstracts the complexity of the one below it.

-  **`ZedCamera`**: The lowest-level core class. It is a thread-safe wrapper that directly manages a single Zed device. Its sole responsibility is to connect to the device, continuously acquire and process frames, and provide thread-safe access to the latest data (images, frames, intrinsics).
    ```bash
    # get images
    uv run examples/run_zed.py
    ```
-  **`Camera`**: This class acts as a high-level container for a single, complete camera setup. It instantiates and coordinates one `ZedCamera` object along with its optional `Viewer` and `Recorder` modules. The `Viewer` handles rendering frames to the screen, while the `Recorder` handles writing frames to disk.
    ```bash
    # live view + recording
    uv run examples/run_camera.py
    ```
-  **`System`**: The top-level manager. This class is responsible for managing a collection of `Camera` objects, allowing you to launch, update, and shut down an entire multi-camera system with simple commands.
    ```bash
    # deal with multiple cameras in the environment
    uv run examples/run_system.py
    ```

### Default Camera Settings

You need to provide configuration for your customized camera usage. These are the default settings. You only need to include those parameters different from the default values in your configuration.

```python
camera_config = {
    "enable_viewer": False,             # set to True if you need a window to see live streaming images
    "enable_recorder": False,           # set to True if you need to record the camera streaming
    
    "specifications": {
        "fps": 30,
        "size": (1280, 720),
        "auto_exposure": True,
    },
    
    "viewer": {                         # update this dict with your preference if viewer enabled
        "fps": 30,
        "show_color": True,
        "show_depth": False,
    },
    
    "recorder": {                       # update this dict with your preference if recorder enabled 
        "fps": 10,
        "save_dir": "./recordings",
        "save_name": current_time,
        "save_with_overlays": False,
        "auto_start": True,             # applicable to set False ONLY when viewer is enabled. If False, press s to start recording at any time point during the experiment.
    }
}

overlays_config = [
    {"type": "dot",
     "xy": xy,
     "radius": 6,
     "color": (0, 255, 0)
     },
    {"type": "text",
     "content": text,
     "position": (50, 50),
     "color": (0, 0, 255)
     }
]
```