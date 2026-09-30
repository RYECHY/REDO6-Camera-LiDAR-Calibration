#!/usr/bin/env python3
"""Check a local camera-LiDAR YAML and derive its inverse transform.

This generic utility does not measure accuracy, modify files, connect to ROS,
or transmit any information. The bundled input is the user-authorized final calibration.
"""
import argparse
from pathlib import Path
import shlex
import sys

import numpy as np
import yaml


def quaternion_xyzw(matrix):
    """Convert a proper rotation to a normalized quaternion, with w >= 0."""
    trace = np.trace(matrix)
    if trace > 0:
        scale = np.sqrt(trace + 1.0) * 2.0
        q = np.array([(matrix[2, 1] - matrix[1, 2]) / scale,
                      (matrix[0, 2] - matrix[2, 0]) / scale,
                      (matrix[1, 0] - matrix[0, 1]) / scale, scale / 4.0])
    else:
        i = int(np.argmax(np.diag(matrix)))
        j, k = (i + 1) % 3, (i + 2) % 3
        scale = np.sqrt(1 + matrix[i, i] - matrix[j, j] - matrix[k, k]) * 2
        q = np.zeros(4)
        q[i] = scale / 4
        q[j] = (matrix[j, i] + matrix[i, j]) / scale
        q[k] = (matrix[k, i] + matrix[i, k]) / scale
        q[3] = (matrix[k, j] - matrix[j, k]) / scale
    q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q


def read_transform(path, tolerance):
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    rotation = np.asarray(data['T_cam_lidar']['rotation'], dtype=float)
    if rotation.shape == (9,):
        rotation = rotation.reshape(3, 3)
    if rotation.shape != (3, 3):
        raise ValueError('rotation must be a row-major list of 9 values or a 3x3 array')
    translation = np.asarray(data['T_cam_lidar']['translation'], dtype=float)
    if translation.shape != (3,) or not np.isfinite(rotation).all() or not np.isfinite(translation).all():
        raise ValueError('Invalid translation shape or nonfinite transform values')
    error = np.linalg.norm(rotation.T @ rotation - np.eye(3))
    determinant = np.linalg.det(rotation)
    if error > tolerance or abs(determinant - 1) > tolerance:
        raise ValueError('rotation fails orthogonality/determinant checks: det={}, error={}'.format(determinant, error))
    camera = data['camera']
    intrinsics = np.asarray([camera[name] for name in ('fx', 'fy', 'cx', 'cy')], dtype=float)
    if not np.isfinite(intrinsics).all() or intrinsics[0] <= 0 or intrinsics[1] <= 0:
        raise ValueError('Camera intrinsics must be finite with positive focal lengths')
    for name in ('width', 'height'):
        value = camera[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError('Image dimensions must be positive integers')
    distortion = np.asarray(camera['distortion'], dtype=float)
    if camera.get('distortion_model') != 'plumb_bob' or distortion.shape != (5,) or not np.isfinite(distortion).all():
        raise ValueError('This utility expects plumb_bob with five finite values [k1,k2,p1,p2,k3]')
    u, _, vh = np.linalg.svd(rotation)
    proper_rotation = u @ vh
    inverse_rotation = proper_rotation.T
    inverse_translation = -inverse_rotation @ translation
    quaternion = quaternion_xyzw(inverse_rotation)
    return data, determinant, error, np.linalg.norm(proper_rotation - rotation), inverse_rotation, inverse_translation, quaternion


def main():
    default = Path(__file__).resolve().parents[1] / 'config/front_camera_mid360_extrinsics_final.yaml'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('calibration', nargs='?', type=Path, default=default)
    parser.add_argument('--rotation-tolerance', type=float, default=1e-5,
                        help='Numerical validity tolerance; not an accuracy threshold')
    parser.add_argument('--print-tf', action='store_true', help='Print, but do not execute, a ROS static TF command')
    parser.add_argument('--parent', help='Confirmed LiDAR parent frame, required with --print-tf')
    parser.add_argument('--child', help='Confirmed camera optical child frame, required with --print-tf')
    args = parser.parse_args()
    if not np.isfinite(args.rotation_tolerance) or not 0 < args.rotation_tolerance <= 1e-3:
        parser.error('--rotation-tolerance must be positive and at most 1e-3')
    if args.print_tf and (not args.parent or not args.child or args.parent == args.child):
        parser.error('--print-tf requires distinct, confirmed --parent and --child frame names')
    data, determinant, error, correction, rotation, translation, quaternion = read_transform(
        args.calibration.expanduser(), args.rotation_tolerance)
    if data.get('synthetic_example'):
        print('SYNTHETIC EXAMPLE: these values are not measurements and must not be deployed.')
        if args.print_tf:
            parser.error('TF printing is disabled for the bundled synthetic example')
    print('PASS: numerical validity only; not proof of calibration accuracy.')
    print('det(R)={:.10f}; ||R^T R-I||_F={:.3e}'.format(determinant, error))
    print('Nearest proper rotation correction={:.3e}; source file unchanged.'.format(correction))
    print('Input convention: p_C = R_CL p_L + t_CL (translation in metres)')
    print('Inverse rotation (R_LC):\n', rotation)
    print('Inverse translation (t_LC):', translation.tolist())
    print('Inverse quaternion (x,y,z,w):', quaternion.tolist())
    if args.print_tf:
        parts = ['ros2', 'run', 'tf2_ros', 'static_transform_publisher']
        for flag, value in zip(('--x', '--y', '--z', '--qx', '--qy', '--qz', '--qw'), list(translation) + list(quaternion)):
            parts.extend([flag, '{:.10f}'.format(value)])
        parts.extend(['--frame-id', args.parent, '--child-frame-id', args.child])
        print('PRINT ONLY. Check existing publishers, frame definitions, and image model before using:')
        print(' '.join(shlex.quote(part) for part in parts))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, AssertionError, yaml.YAMLError) as error:
        print('FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
