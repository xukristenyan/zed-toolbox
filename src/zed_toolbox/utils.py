import cv2
import numpy as np


def draw_overlays(image, overlays):
    copied = image.copy()

    for item in overlays:
        if item["type"] == "dot":
            if item["xy"] is not None:
                cv2.circle(copied, (int(item["xy"][0]), int(item["xy"][1])), item.get("radius", 6), item.get("color", (0, 255, 0)), -1)

        if item["type"] == "text":
            cv2.putText(copied, text=item["text"], org=item.get("position", [50, 50]), color=item.get("color", (0, 0, 255)), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=3)

        if item["type"] == "box":
            pass
    
    return copied


def adjust_depth_image(depth_image_float, min_depth=0.01, max_depth=3):
    depth_clipped = np.clip(depth_image_float, min_depth, max_depth)

    depth_normalized = cv2.normalize(depth_clipped, None, 0, 255, 
                                     cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    depth_normalized[np.isnan(depth_image_float)] = 0 

    return cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)


def quit_keypress():
    key = cv2.waitKey(1)
    # press ESC
    return key == 27


def start_keypress():
    key = cv2.waitKey(1)
    # press s
    return key == ord('s')


def end_keypress():
    key = cv2.waitKey(1)
    # press e
    return key == ord('e')


def save_calibration_file(filepath, K, baseline):        
    k_flat = " ".join([str(val) for val in K.flatten()])
    baseline_str = f"{baseline:.18f}" 

    with open(filepath, 'w') as f:
        f.write(f"{k_flat}\n")
        f.write(f"{baseline_str}\n")
    print(f"Successfully saved calibration file to {filepath}")