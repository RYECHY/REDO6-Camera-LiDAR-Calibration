#!/usr/bin/env python3

import numpy as np
import rclpy

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from livox_ros_driver2.msg import CustomMsg
from sensor_msgs.msg import PointCloud2, PointField


class RawLidarCloud(Node):

    def __init__(self):
        super().__init__('raw_lidar_cloud')

        self.sub = self.create_subscription(
            CustomMsg,
            '/livox/lidar',
            self.callback,
            qos_profile_sensor_data
        )

        self.pub = self.create_publisher(
            PointCloud2,
            '/lidar_camera/raw_points',
            10
        )

        self.frame_count = 0

        self.get_logger().info('Raw LiDAR cloud node started')
        self.get_logger().info('Input : /livox/lidar')
        self.get_logger().info('Output: /lidar_camera/raw_points')

    def callback(self, msg):

        if msg.point_num == 0:
            return

        points = np.array(
            [
                [p.x, p.y, p.z, float(p.reflectivity)]
                for p in msg.points
            ],
            dtype=np.float32
        )

        valid = np.isfinite(points[:, :3]).all(axis=1)
        points = points[valid]

        if len(points) == 0:
            return

        out = PointCloud2()

        out.header = msg.header
        out.header.frame_id = 'livox_frame'

        out.height = 1
        out.width = len(points)

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
                name='intensity',
                offset=12,
                datatype=PointField.FLOAT32,
                count=1
            )
        ]

        out.is_bigendian = False
        out.point_step = 16
        out.row_step = out.point_step * out.width
        out.is_dense = True
        out.data = points.tobytes()

        self.pub.publish(out)

        self.frame_count += 1

        if self.frame_count % 10 == 0:
            self.get_logger().info(
                f'Raw LiDAR points={out.width}'
            )


def main(args=None):

    rclpy.init(args=args)

    node = RawLidarCloud()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
