from zed_toolbox import Zed
import cv2

def save_calibration_file(filepath, K, baseline):        
    k_flat = " ".join([str(val) for val in K.flatten()])
    baseline_str = f"{baseline:.18f}" 

    with open(filepath, 'w') as f:
        f.write(f"{k_flat}\n")
        f.write(f"{baseline_str}\n")
    print(f"Successfully saved calibration file to {filepath}")


def main():
    serial = 24944966

    specs = {
        "fps": 30,
        "size": (1280, 720)
    }

    camera = None
    try:
        camera = Zed(serial, specs)
        camera.launch()

        while True:
            state = camera.get_current_state()

            if state["left_image"] is not None and state["right_image"] is not None:
                break

        cv2.imwrite("ir_left.png", state["left_image"])
        cv2.imwrite("ir_right.png", state["right_image"])

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