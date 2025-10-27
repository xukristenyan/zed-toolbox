'''
This file is to help find the serial number of a new Zed camera.
'''

import pyzed.sl as sl


def get_zed_serial_number():
    zed = sl.Camera()
    
    init_params = sl.InitParameters()
        err = zed.open(init_params)
    
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED camera: {err}")
        return None
    
    info = zed.get_camera_information()
    serial_number = info.serial_number
    
    print(f"--- ZED Camera Detected ---")
    print(f"  Model: {info.camera_model}")
    print(f"  Serial Number: {serial_number}")
    
    # Close the camera
    zed.close()
    return serial_number



if __name__ == "__main__":
    get_zed_serial_number()