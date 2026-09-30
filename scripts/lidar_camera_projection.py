#!/usr/bin/env python3

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from livox_ros_driver2.msg import CustomMsg
from sensor_msgs.msg import CompressedImage, PointCloud2, PointField


class LidarCameraProjection(Node):

    def __init__(self):
        super().__init__('lidar_camera_projection')

        # ============================================================
        # REDO6 FINAL CALIBRATION
        # P_camera = R_cam_lidar * P_lidar + t_cam_lidar
        # ============================================================

        self.width = 1920
        self.height = 1080

        self.K = np.array([
            [796.164262460850, 0.0,              998.040267016264],
            [0.0,              796.565439605239, 586.594945318602],
            [0.0,              0.0,              1.0]
        ], dtype=np.float64)

        self.D = np.array([
            -0.107115015572,
             0.014040533509,
             0.000011518208,
             0.000091001532,
            -0.000901838357
        ], dtype=np.float64)

        self.R_cam_lidar = np.array([
            [-0.020792, -0.999597,  0.019323],
            [ 0.520325, -0.027322, -0.853531],
            [ 0.853715, -0.007692,  0.520683]
        ], dtype=np.float64)

        self.t_cam_lidar = np.array([
             0.002680,
            -0.253080,
             0.059294
        ], dtype=np.float64)

        # Latest camera image
        self.latest_image = None
        self.latest_image_header = None

        # ROS subscribers
        self.lidar_sub = self.create_subscription(
            CustomMsg,
            '/livox/lidar',
            self.lidar_callback,
            qos_profile_sensor_data
        )

        self.image_sub = self.create_subscription(
            CompressedImage,
            '/front_camera/image_compressed',
            self.image_callback,
            qos_profile_sensor_data
        )

        # ROS publishers
        self.corr_pub = self.create_publisher(
            PointCloud2,
            '/pixel_point_correspondence',
            10
        )

        self.image_pub = self.create_publisher(
            CompressedImage,
            '/projection_image/compressed',
            10
        )

        self.frame_count = 0

        self.get_logger().info(
            'LiDAR-camera projection node started'
        )
        self.get_logger().info(
            'LiDAR: /livox/lidar [livox_frame]'
        )
        self.get_logger().info(
            'Camera: /front_camera/image_compressed [camera_frame]'
        )
        self.get_logger().info(
            'Output: /pixel_point_correspondence'
        )
        self.get_logger().info(
            'Output: /projection_image/compressed'
        )

    def image_callback(self, msg):

        np_arr = np.frombuffer(msg.data, dtype=np.uint8)

        image = cv2.imdecode(
            np_arr,
            cv2.IMREAD_COLOR
        )

        if image is None:
            self.get_logger().warning(
                'Failed to decode camera image'
            )
            return

        self.latest_image = image
        self.latest_image_header = msg.header

    def lidar_callback(self, msg):

        if self.latest_image is None:
            return

        if msg.point_num == 0:
            return

        # ------------------------------------------------------------
        # CustomMsg -> numpy
        # Coordinates are in livox_frame
        # ------------------------------------------------------------

        points_lidar = np.array(
            [
                [p.x, p.y, p.z]
                for p in msg.points
            ],
            dtype=np.float64
        )

        finite_mask = np.isfinite(points_lidar).all(axis=1)

        points_lidar = points_lidar[finite_mask]

        if len(points_lidar) == 0:
            return

        # ------------------------------------------------------------
        # LiDAR frame -> Camera frame
        #
        # Pc = Rcl * Pl + tcl
        # ------------------------------------------------------------

        points_camera = (
            self.R_cam_lidar @ points_lidar.T
        ).T + self.t_cam_lidar

        # Only keep points in front of camera
        front_mask = points_camera[:, 2] > 0.10

        points_lidar = points_lidar[front_mask]
        points_camera = points_camera[front_mask]

        if len(points_camera) == 0:
            return

        # ------------------------------------------------------------
        # Camera 3D -> distorted image pixel
        #
        # OpenCV plumb_bob:
        # D = [k1, k2, p1, p2, k3]
        # ------------------------------------------------------------

        image_points, _ = cv2.projectPoints(
            points_camera.reshape(-1, 1, 3),
            np.zeros((3, 1), dtype=np.float64),
            np.zeros((3, 1), dtype=np.float64),
            self.K,
            self.D
        )

        uv = image_points.reshape(-1, 2)

        u = uv[:, 0]
        v = uv[:, 1]

        image = self.latest_image.copy()

        h, w = image.shape[:2]

        inside_mask = (
            (u >= 0.0) &
            (u < float(w)) &
            (v >= 0.0) &
            (v < float(h))
        )

        points_lidar_valid = points_lidar[inside_mask]
        points_camera_valid = points_camera[inside_mask]

        u_valid = u[inside_mask]
        v_valid = v[inside_mask]

        if len(points_lidar_valid) == 0:
            return

        # ------------------------------------------------------------
        # Publish correspondence PointCloud2
        #
        # x,y,z  : original point in livox_frame
        # u,v    : pixel in camera image
        # depth  : Z in camera_frame
        # ------------------------------------------------------------

        corr = np.column_stack((
            points_lidar_valid[:, 0],
            points_lidar_valid[:, 1],
            points_lidar_valid[:, 2],
            u_valid,
            v_valid,
            points_camera_valid[:, 2]
        )).astype(np.float32)

        cloud_msg = PointCloud2()

        cloud_msg.header = msg.header
        cloud_msg.header.frame_id = 'livox_frame'

        cloud_msg.height = 1
        cloud_msg.width = corr.shape[0]

        cloud_msg.fields = [
            PointField(
                name='x',
                offset=0,
                datatype=PointField.FLOAT32,
                count=1
            ),
            PointField(
                name='y',
                offset=4,
                datatype=PointField.FLOAT32,
                count=1
            ),
            PointField(
                name='z',
                offset=8,
                datatype=PointField.FLOAT32,
                count=1
            ),
            PointField(
                name='u',
                offset=12,
                datatype=PointField.FLOAT32,
                count=1
            ),
            PointField(
                name='v',
                offset=16,
                datatype=PointField.FLOAT32,
                count=1
            ),
            PointField(
                name='depth',
                offset=20,
                datatype=PointField.FLOAT32,
                count=1
            )
        ]

        cloud_msg.is_bigendian = False
        cloud_msg.point_step = 24
        cloud_msg.row_step = cloud_msg.point_step * cloud_msg.width
        cloud_msg.is_dense = True
        cloud_msg.data = corr.tobytes()

        self.corr_pub.publish(cloud_msg)

        # ------------------------------------------------------------
        # Draw projected LiDAR points
        # ------------------------------------------------------------

        # Draw half of them to keep image readable and save CPU
        for i in range(0, len(u_valid), 2):

            px = int(round(u_valid[i]))
            py = int(round(v_valid[i]))

            if 0 <= px < w and 0 <= py < h:

                cv2.circle(
                    image,
                    (px, py),
                    2,
                    (0, 0, 255),
                    -1,
                    cv2.LINE_AA
                )

        cv2.putText(
            image,
            'REDO6 LiDAR -> Camera Projection',
            (30, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        text = (
            f'LiDAR: {msg.point_num}  '
            f'Projected: {len(u_valid)}'
        )

        cv2.putText(
            image,
            text,
            (30, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        ok, encoded = cv2.imencode(
            '.jpg',
            image,
            [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        )

        if ok:

            out_img = CompressedImage()

            if self.latest_image_header is not None:
                out_img.header = self.latest_image_header

            out_img.header.frame_id = 'camera_frame'
            out_img.format = 'jpeg'
            out_img.data = encoded.tobytes()

            self.image_pub.publish(out_img)

        self.frame_count += 1

        if self.frame_count % 10 == 0:

            self.get_logger().info(
                f'LiDAR={msg.point_num}, '
                f'camera_FOV={len(u_valid)}'
            )


def main(args=None):

    rclpy.init(args=args)

    node = LidarCameraProjection()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
