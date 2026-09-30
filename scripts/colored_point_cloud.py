#!/usr/bin/env python3

import cv2
import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, PointCloud2, PointField


class ColoredPointCloud(Node):

    def __init__(self):
        super().__init__('lidar_camera_colored_cloud')

        self.latest_image = None

        self.image_sub = self.create_subscription(
            CompressedImage,
            '/front_camera/image_compressed',
            self.image_callback,
            qos_profile_sensor_data
        )

        self.corr_sub = self.create_subscription(
            PointCloud2,
            '/pixel_point_correspondence',
            self.corr_callback,
            10
        )

        self.cloud_pub = self.create_publisher(
            PointCloud2,
            '/lidar_camera/colored_points',
            10
        )

        self.frame_count = 0

        self.get_logger().info('Colored point cloud node started')
        self.get_logger().info(
            'Input image: /front_camera/image_compressed'
        )
        self.get_logger().info(
            'Input correspondence: /pixel_point_correspondence'
        )
        self.get_logger().info(
            'Output: /lidar_camera/colored_points'
        )

    def image_callback(self, msg):

        data = np.frombuffer(msg.data, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)

        if image is None:
            self.get_logger().warning('Failed to decode camera image')
            return

        self.latest_image = image

    def corr_callback(self, msg):

        if self.latest_image is None:
            return

        if msg.point_step != 24:
            self.get_logger().warning(
                f'Unexpected point_step={msg.point_step}, expected 24'
            )
            return

        if msg.width == 0:
            return

        raw = np.frombuffer(msg.data, dtype=np.float32)

        if raw.size % 6 != 0:
            self.get_logger().warning(
                f'Unexpected correspondence size={raw.size}'
            )
            return

        corr = raw.reshape(-1, 6)

        # Current correspondence definition:
        # x y z = livox_frame
        # u v   = image pixel
        # depth = camera Z
        xyz = corr[:, 0:3].astype(np.float32)
        u = corr[:, 3]
        v = corr[:, 4]

        image = self.latest_image
        h, w = image.shape[:2]

        px = np.rint(u).astype(np.int32)
        py = np.rint(v).astype(np.int32)

        valid = (
            (px >= 0) & (px < w) &
            (py >= 0) & (py < h) &
            np.isfinite(xyz).all(axis=1)
        )

        if not np.any(valid):
            return

        xyz = xyz[valid]
        px = px[valid]
        py = py[valid]

        # OpenCV image = BGR
        bgr = image[py, px]

        b = bgr[:, 0].astype(np.uint32)
        g = bgr[:, 1].astype(np.uint32)
        r = bgr[:, 2].astype(np.uint32)

        # PCL / RViz packed RGB
        rgb_uint = (
            (r << 16) |
            (g << 8) |
            b
        ).astype(np.uint32)

        rgb_float = rgb_uint.view(np.float32)

        cloud = np.empty((xyz.shape[0], 4), dtype=np.float32)
        cloud[:, 0:3] = xyz
        cloud[:, 3] = rgb_float

        out = PointCloud2()

        # Coordinates are still livox_frame coordinates.
        # RViz will transform them to map through TF.
        out.header = msg.header
        out.header.frame_id = 'livox_frame'

        out.height = 1
        out.width = cloud.shape[0]

        out.fields = [
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
                name='rgb',
                offset=12,
                datatype=PointField.FLOAT32,
                count=1
            ),
        ]

        out.is_bigendian = False
        out.point_step = 16
        out.row_step = out.point_step * out.width
        out.is_dense = True
        out.data = cloud.tobytes()

        self.cloud_pub.publish(out)

        self.frame_count += 1

        if self.frame_count % 10 == 0:
            self.get_logger().info(
                f'Colored points={out.width}'
            )


def main(args=None):

    rclpy.init(args=args)

    node = ColoredPointCloud()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
