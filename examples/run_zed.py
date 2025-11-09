from zed_toolbox import ZedCamera
import cv2
from zed_toolbox.utils import save_calibration_file


def main():
    serial = 24944966

    specs = {
        "fps": 30,
        "size": (1280, 720),
        "auto_exposure": False,
    }

    camera = None
    try:
        camera = ZedCamera(serial, specs)
        camera.launch()

        while True:
            state = camera.get_current_state()
            rgb, d = camera.get_rgbd()

            if state["left_image"] is not None and state["right_image"] is not None:
                break

        print(rgb.shape)
        print(d.shape)
        cv2.imwrite("left.png", state["left_image"])
        cv2.imwrite("right.png", state["right_image"])

        K, dist = camera.get_intrinsics()

        baseline = camera.get_baseline()

        print(K)
        print(baseline)

        save_calibration_file(f"./intrin_{str(serial)[-3:]}.txt", K, baseline)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting gracefully.")

    except Exception as e:
        print(f"Unexpected error occurred: {e}")

    finally:
        if camera:
            camera.shutdown()



if __name__ == "__main__":
    main()