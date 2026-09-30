#!/usr/bin/env python3
"""Count and validate PointCloud2 pixel correspondences in a ROS 2 bag.

Newly written public utility. No bag data is bundled and no network is used.
The checks measure message validity, not spatial correspondence accuracy.
"""
import argparse
import json
import math
from pathlib import Path
import struct


def records(message):
    """Read required FLOAT32 fields, respecting offsets, row stride and endian."""
    fields = {field.name: field for field in message.fields}
    required = ('x', 'y', 'z', 'u', 'v', 'depth')
    for name in required:
        field = fields.get(name)
        if field is None or field.datatype != 7 or field.count != 1:
            raise ValueError('Required scalar FLOAT32 field missing: ' + name)
        if field.offset < 0 or field.offset + 4 > message.point_step:
            raise ValueError('Invalid offset: ' + name)
    if message.point_step <= 0 or message.row_step < message.width * message.point_step:
        raise ValueError('Invalid point/row stride')
    if len(message.data) < message.height * message.row_step:
        raise ValueError('PointCloud2 data buffer is too short')
    endian = '>' if message.is_bigendian else '<'
    for row in range(message.height):
        for col in range(message.width):
            start = row * message.row_step + col * message.point_step
            yield tuple(struct.unpack_from(endian + 'f', message.data, start + fields[name].offset)[0]
                        for name in required)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bag', type=Path)
    parser.add_argument('--topic', default='/pixel_point_correspondence')
    parser.add_argument('--storage-id', default='sqlite3', help='Use mcap only with an installed MCAP storage plugin')
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0:
        parser.error('Image dimensions must be positive')
    # ROS imports remain local to this command; --help works without ROS.
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.bag.expanduser()), storage_id=args.storage_id),
                rosbag2_py.ConverterOptions('cdr', 'cdr'))
    types = {item.name: item.type for item in reader.get_all_topics_and_types()}
    if types.get(args.topic) != 'sensor_msgs/msg/PointCloud2':
        parser.error('Selected topic must exist and have type sensor_msgs/msg/PointCloud2')
    message_type = get_message(types[args.topic])
    counts = dict(messages=0, points=0, nonfinite=0, out_of_frame=0, nonpositive_depth=0)
    ranges = {name: [math.inf, -math.inf] for name in ('u', 'v', 'depth')}
    frames = set()
    while reader.has_next():
        name, raw, _ = reader.read_next()
        if name != args.topic:
            continue
        message = deserialize_message(raw, message_type)
        counts['messages'] += 1
        frames.add(message.header.frame_id)
        for point in records(message):
            counts['points'] += 1
            if not all(math.isfinite(value) for value in point):
                counts['nonfinite'] += 1
                continue
            u, v, depth = point[3:]
            counts['out_of_frame'] += int(not (0 <= u < args.width and 0 <= v < args.height))
            counts['nonpositive_depth'] += int(depth <= 0)
            for name, value in zip(('u', 'v', 'depth'), (u, v, depth)):
                ranges[name][0] = min(ranges[name][0], value)
                ranges[name][1] = max(ranges[name][1], value)
    result = {'counts': counts, 'frames': sorted(frames),
              'ranges': {name: values if math.isfinite(values[0]) else None for name, values in ranges.items()},
              'note': 'Message validity checks only; not proof of accurate projection.'}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if counts['messages'] == 0 or counts['points'] == 0 or any(counts[name] for name in ('nonfinite', 'out_of_frame', 'nonpositive_depth')):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
