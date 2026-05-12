"""
Stream directly from a ZED camera (no Camera/Viewer/Recorder).

Saves N frames per enabled stream to disk and prints intrinsics + baseline.
SSH-friendly. Edit `config` to switch between modes (e.g. add "depth").
"""
import time
from pathlib import Path

import cv2
import numpy as np

from zed_toolbox import ZedCamera
from zed_toolbox.config import ZedConfig


def main():
    # ===== YOUR CHANGES =====
    serial = 24944966

    config = ZedConfig(
        streams=["left", "right"],
        # streams=["left", "depth"],   # uncomment to test on-device depth (NEURAL)
    )

    out_dir = Path("./recordings/smoke_test")
    n_frames = 5
    # ========================

    out_dir.mkdir(parents=True, exist_ok=True)

    camera = ZedCamera(serial, config)
    try:
        camera.launch()

        intr = camera.get_intrinsics()
        print(f"\nK (left):\n{intr['matrix']}")
        print(f"baseline: {intr['baseline']:.6f} m")

        # Wait up to 5s for first frame
        for _ in range(100):
            if camera.get_current_state():
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("No frames received within 5s")

        for i in range(n_frames):
            state = camera.get_current_state()
            if not state:
                time.sleep(0.05)
                continue
            for name, img in state.items():
                if name == "depth":
                    clipped = np.clip(img, 0.01, 3.0)
                    norm = cv2.normalize(clipped, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                    norm[np.isnan(img)] = 0
                    colormap = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
                    cv2.imwrite(str(out_dir / f"{i:03d}_depth_colormap.png"), colormap)
                    np.savez_compressed(out_dir / f"{i:03d}_depth.npz", depth=img)  # raw float meters
                else:
                    cv2.imwrite(str(out_dir / f"{i:03d}_{name}.png"), img)
            time.sleep(0.1)

        print(f"\nSaved {n_frames} frames/stream to {out_dir.resolve()}")
        print(f"Streams captured: {list(state.keys())}")

    finally:
        camera.shutdown()


if __name__ == "__main__":
    main()
