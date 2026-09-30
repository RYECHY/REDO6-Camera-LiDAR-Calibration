#!/usr/bin/env python3
"""New public launch example; requires the user's separately installed mapper.

No complete mapper configuration or full source tree is distributed.
Selected mapper modifications are supplied separately as upstream patches.
This file was syntax-checked only; ROS execution was not tested here.
"""
from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('livo_params_file', description='Absolute path to your complete compatible LIVO configuration'),
        DeclareLaunchArgument('camera_params_file', default_value=str(root / 'config/fast_livo2/machine_dog_redo6_camera.yaml')),
        DeclareLaunchArgument('image_topic', default_value='/front_camera/image_compressed'),
        DeclareLaunchArgument('raw_image_topic', default_value='/front_camera/image_raw_redo6'),
        Node(package='demo_nodes_cpp', executable='parameter_blackboard', name='parameter_blackboard',
             parameters=[LaunchConfiguration('camera_params_file')], output='screen'),
        Node(package='image_transport', executable='republish', name='calibration_image_republish',
             arguments=['compressed', 'raw'],
             remappings=[('in/compressed', LaunchConfiguration('image_topic')),
                         ('out', LaunchConfiguration('raw_image_topic'))], output='screen'),
        Node(package='fast_livo', executable='fastlivo_mapping', name='laserMapping',
             parameters=[LaunchConfiguration('livo_params_file')], output='screen'),
    ])
