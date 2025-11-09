from zed_toolbox import ZedCamera
import open3d as o3d

def main():
    serial = 24944966
    specs = {
        "fps": 30,
        "size": (1280, 720)
    }

    camera = None
    try:
        camera = ZedCamera(serial, specs)
        camera.launch()

        while True:
            rgb_raw, d_raw = camera.get_rgbd()
            if rgb_raw is not None and d_raw is not None:
                break
        
        rgb = rgb_raw[:, :, ::-1].copy()
        d = d_raw.copy()

        o3d_rgb = o3d.geometry.Image(rgb)
        o3d_depth = o3d.geometry.Image(d)

        rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(o3d_rgb, o3d_depth, depth_scale=1.0, depth_trunc=3.0, convert_rgb_to_intensity=False)

        K, _ = camera.get_intrinsics()
        fx = K[0, 0]
        fy = K[1, 1]
        cx = K[0, 2]
        cy = K[1, 2]
        width, height = camera.size

        intrinsics = o3d.camera.PinholeCameraIntrinsic(width, height, fx, fy, cx, cy)

        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, intrinsics)

        o3d.visualization.draw_geometries([pcd])


    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting gracefully.")

    except Exception as e:
        print(f"Unexpected error occurred: {e}")

    finally:
        if camera:
            camera.shutdown()


if __name__ == "__main__":
    main()