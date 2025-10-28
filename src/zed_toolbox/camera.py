import time
from .zed import ZedCamera
from .viewer import Viewer
from .recorder import Recorder
from .utils import start_keypress, end_keypress


class Camera:
    '''
    A high-level container for a single Zed device managing its core camera stream, viewer, and recorder components.
    '''
    def __init__(self, serial, config):
        self.serial = serial

        zed_config = config.get("specifications", {})
        self.zed_camera = ZedCamera(self.serial, zed_config)

        if config.get("enable_viewer", True):
            conf = config.get("viewer", {})
            viewer_config = {
                "show_color": conf.get("show_color", True),
                "show_depth": conf.get("show_depth", False),
                "fps": conf.get("fps", 30)
            }
            self.viewer = Viewer(self.serial, viewer_config)
        else:
            self.viewer = None

        if config.get("enable_recorder", False):
            conf = config.get("recorder", {})
            save_time = time.strftime("%Y%m%d_%H%M%S")
            recorder_config = {
                "save_dir": conf.get("save_dir", "./recordings"),
                "save_name": conf.get("save_name", f"{save_time}"),
                "fps": conf.get("fps", 10),
                "save_with_overlays": conf.get("save_with_overlays", False),
            }
            self.recorder = Recorder(self.serial, recorder_config)
            self.auto_start = conf.get("auto_start", True)
        else:
            self.recorder = None

        self.is_alive = False
        self.recording_started = False

        self.state = {"timestamp": None, "left_image": None, "right_image": None, "depth": None}


    def launch(self):
        self.zed_camera.launch()
        self.is_alive = True


    def update(self, overlays=None):
        '''
        Fetches the latest frames and updates the viewer and recorder.
        This is meant to be called from an external loop.
        '''
        state = self.zed_camera.get_current_state()
        self.state.update(state)

        if self.state["left_image"] is not None and self.state["depth"] is not None:

            if self.recorder:
                if not self.recording_started:
                    if self.auto_start:
                        self.recording_started = True
                        print(f"[Recorder {str(self.serial)[-3:]}] Recording started !!!")

                    elif start_keypress():
                        self.recording_started = True
                        print(f"[Recorder {str(self.serial)[-3:]}] Recording started !!!")

                if self.recording_started:
                    self.recorder.update(self.state["left_image"], self.state["depth"], overlays)

                    if end_keypress():
                        self.recording_started = False
                        print(f"[Recorder {str(self.serial)[-3:]}] Recording stopped !!!")

            if self.viewer:
                self.viewer.update(self.state["left_image"], self.state["depth"], overlays)
                if not self.viewer.viewer_alive:
                    self.is_alive = False


    def get_current_state(self):
        return self.state


    def shutdown(self):
        if self.recorder:
            self.recorder.stop()
        self.zed_camera.shutdown()


    def control_recording(self, start):
        self.recording_started = start