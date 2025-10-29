import time
import threading
import numpy as np
import pyzed.sl as sl
from PIL import Image


class ZedCamera:
    def __init__(self, serial, config: dict):
        self.serial = serial
        if not self.serial:
            raise ValueError("Missing camera serial number.")
        
        self.fps = config.get("fps", 30)
        self.size = config.get("size", (1280, 720))

        self.auto_exposure = config.get("auto_exposure", False)
        self.exposure = config.get("exposure", 80)  # Manual exposure value (1-100)

        # instantiate a ZED camera
        self.camera = sl.Camera()
        self.init_params = sl.InitParameters()
        self.init_params.set_from_serial_number(self.serial)
        self.init_params.camera_fps = self.fps
        self.init_params.camera_resolution = sl.RESOLUTION.HD720
        self.init_params.depth_mode = sl.DEPTH_MODE.NEURAL 
        self.init_params.coordinate_units = sl.UNIT.METER 

        self.closed = True

        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.state = {"timestamp": None, "left_image": None, "right_image": None, "depth": None}
        self.intrinsics_cache = None


    def launch(self):
        err = self.camera.open(self.init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise Exception(f"[Zed {str(self.serial)[-3:]}] Failed to launch. Check camera connection!")

        self.camera.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 1 if self.auto_exposure else 0)

        self.closed = False

        self._thread = threading.Thread(target=self._update_frame, daemon=True)
        self._thread.start()

        info = self.camera.get_camera_information()
        calib = info.camera_configuration.calibration_parameters.left_cam
        self.intrinsics_cache = {
            "fx": calib.fx, "fy": calib.fy,
            "cx": calib.cx, "cy": calib.cy
        }

        print(f"[Zed {str(self.serial)[-3:]}] Launched!")


    def shutdown(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

        self.camera.close()
        self.closed = True

        print(f"[Zed {str(self.serial)[-3:]}] Shutdown complete.")


    def _update_frame(self):
        left = sl.Mat()
        right = sl.Mat()
        depth = sl.Mat()
        
        while not self.closed and not self._stop_event.is_set() and self.camera.grab() == sl.ERROR_CODE.SUCCESS:
            self.camera.retrieve_image(left, sl.VIEW.LEFT)
            self.camera.retrieve_image(right, sl.VIEW.RIGHT)
            self.camera.retrieve_measure(depth, sl.MEASURE.DEPTH)
            timestamp = self.camera.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_milliseconds()

            left_image = self.prep_img(left)
            right_image = self.prep_img(right)
            # now in np.array(720, 1080, (r, g, b))
            depth_info = depth.get_data()

            with self._lock:
                self.state.update({"timestamp": timestamp, 
                                    "left_image": left_image,
                                    "right_image": right_image,
                                    "depth": depth_info})


    def prep_img(self, raw_img):
        # remove alpha layer
        img = raw_img.get_data()[:,:,:3]
        
        # # BGR -> RGB
        # img = img[:,:,::-1]
        
        # resize
        image_pil = Image.fromarray(img)
        image_resized_pil = image_pil.resize(self.size)
        resized_image = np.array(image_resized_pil)

        return resized_image


    def get_current_state(self):
        with self._lock:
            return self.state.copy()


    def get_intrinsics(self):
        info = self.camera.get_camera_information()
        calib_params = info.camera_configuration.calibration_parameters
        calib = calib_params.left_cam
        
        fx, fy = calib.fx, calib.fy
        cx, cy = calib.cx, calib.cy
        K = np.array([
            [fx, 0,  cx],
            [0,  fy, cy],
            [0,  0,  1]
        ])

        disto = calib.disto
        
        return K, disto


    def get_baseline(self):
        info = self.camera.get_camera_information()
        stereo_transform = info.camera_configuration.calibration_parameters.stereo_transform

        translation = stereo_transform.get_translation().get()
        baseline = translation[0]

        return baseline


    def get_rgbd(self):
        with self._lock:
            return self.state.copy()["left_image"], self.state.copy()["depth"]
        

    def deproject_to_3d(self, point):
        u, v = point
        depth_map = self.state.get("depth")
        if depth_map is None:
            return None, None, None

        height, width = depth_map.shape

        u, v = int(u), int(v)
        Z = depth_map[v, u]

        if not np.isfinite(Z):
            return None, None, None
        
        fx = self.intrinsics_cache["fx"]
        fy = self.intrinsics_cache["fy"]
        cx = self.intrinsics_cache["cx"]
        cy = self.intrinsics_cache["cy"]

        X = ((u - cx) * Z) / fx
        Y = ((v - cy) * Z) / fy

        return X, Y, Z