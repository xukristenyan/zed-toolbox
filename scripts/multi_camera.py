"""
Two ZED cameras (main + side) with synchronized start/stop recording.

Press 's' to start recording on all cameras, 'e' to stop, ESC to quit.
"""
import time

from zed_toolbox import (
    CameraSystem, CameraConfig, ZedConfig, ViewerConfig, RecorderConfig,
    KeyListener,
)


def main():
    serial_main = 24944966
    serial_side = 33261276

    common_zed = lambda: ZedConfig(streams=["left", "right"])
    common_rec = lambda: RecorderConfig(streams=["left", "right"], save_name="trial")

    configs = {
        serial_main: CameraConfig(
            zed=common_zed(),
            viewer=ViewerConfig(show=["left"]),
            recorder=common_rec(),
        ),
        serial_side: CameraConfig(
            zed=common_zed(),
            viewer=ViewerConfig(show=["left"]),
            recorder=common_rec(),
        ),
    }

    system = CameraSystem(configs)

    print("Press 's' to start recording (all cams), 'e' to stop, ESC to quit.")
    system.launch()

    try:
        with KeyListener() as keys:
            while system.is_alive:
                system.get_observations()
                if keys.consume_pressed("s"):
                    system.start_recording()
                if keys.consume_pressed("e"):
                    system.stop_recording()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)

    finally:
        system.shutdown()


if __name__ == "__main__":
    main()
