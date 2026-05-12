"""Live view from a ZED camera, no recording. ESC to quit."""
import time

from zed_toolbox import (
    Camera, CameraConfig, ZedConfig, ViewerConfig, KeyListener,
)


def main():
    serial = 24944966
    cfg = CameraConfig(
        zed=ZedConfig(streams=["left", "depth"]),
        viewer=ViewerConfig(show=["left", "depth"]),
    )
    cam = Camera(serial, cfg)

    print("Press ESC to quit.")
    cam.launch()
    try:
        with KeyListener() as keys:
            while cam.is_alive:
                cam.get_observations()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)
    finally:
        cam.shutdown()


if __name__ == "__main__":
    main()
