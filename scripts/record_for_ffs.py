"""
Record left + right stereo pair for offline Fast-FoundationStereo replay.

Output (per session):
    cam_<last3>_left.mp4 + cam_<last3>_left.npz +
    cam_<last3>_right.npz + cam_<last3>_calibration.json.

The .npz pair plus calibration.json is everything FFS needs to re-infer
depth offline; left.mp4 is preserved for visual review.

Press 's' to start, 'e' to stop, ESC to quit.
"""
import time

from zed_toolbox import (
    Camera, CameraConfig, ZedConfig, RecorderConfig, KeyListener,
)


def main():
    serial = 24944966
    cfg = CameraConfig(
        zed=ZedConfig(
            streams=["left", "right"],   # ZED on-device depth disabled (auto-coerced)
        ),
        recorder=RecorderConfig(
            streams=["left", "right"],   # "right" triggers left.npz + right.npz + calibration.json
            save_name="ffs_trial",
            fps=10,
        ),
    )
    cam = Camera(serial, cfg)

    print("Press 's' to start recording, 'e' to stop, ESC to quit.")
    cam.launch()

    try:
        with KeyListener() as keys:
            while cam.is_alive:
                cam.get_observations()
                if keys.consume_pressed("s"):
                    cam.start_recording()
                if keys.consume_pressed("e"):
                    cam.stop_recording()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)

    finally:
        cam.shutdown()


if __name__ == "__main__":
    main()
