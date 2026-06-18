#!/usr/bin/env python3

import os
import yaml

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    OpaqueFunction
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

from ament_index_python.packages import get_package_share_directory
from nav2_common.launch import RewrittenYaml


def generate_launch_description():

    bcr_bot_pkg = get_package_share_directory('bcr_bot')

    use_sim_time = LaunchConfiguration('use_sim_time')

    robots_config = LaunchConfiguration(
        'robots_config'
    )

    def launch_setup(context, *args, **kwargs):

        config_file = robots_config.perform(context)

        with open(config_file, 'r') as f:
            robots = yaml.safe_load(f).get('robots', [])

        robot_groups = []

        ekf_yaml = os.path.join(
            bcr_bot_pkg,
            'config',
            'ekf.yaml'
        )

        amcl_yaml = os.path.join(
            bcr_bot_pkg,
            'config',
            'amcl.yaml'
        )

        for robot in robots:

            ns = robot['name']

          

            ekf_node = Node(
                package='robot_localization',
                executable='ekf_node',
                name='ekf_filter_node',
                output='screen',
                parameters=[
                    ekf_yaml,
                    {
                        'use_sim_time': use_sim_time,
                        'odom_frame': f'{ns}/odom',
                        'base_link_frame': f'{ns}/base_footprint',
                        'world_frame': f'{ns}/odom',
                        'map_frame': 'map',
                    }
                ],
            )

            amcl_node = Node(
                package='nav2_amcl',
                executable='amcl',
                name='amcl',
                output='screen',
                parameters=[
                    amcl_yaml,
                    {
                        'use_sim_time': use_sim_time,
                        'base_frame_id': f'{ns}/base_footprint',
                        'odom_frame_id': f'{ns}/odom',
                        'global_frame_id': 'map',

                        'initial_pose.x': float(robot.get('x', 0.0)),
                        'initial_pose.y': float(robot.get('y', 0.0)),
                        'initial_pose.yaw': float(robot.get('yaw', 0.0)),
                    }
                ]
            )
            amcl_lifecycle = Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_amcl',
                output='screen',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'autostart': True,
                    'node_names': ['amcl']
                }],
            )

            robot_groups.append(
                GroupAction([
                    PushRosNamespace(ns),

                    ekf_node,

                    amcl_node,

                    amcl_lifecycle,
                ])
            )
        map_server = Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[{
                'yaml_filename': os.path.join(
                    bcr_bot_pkg,
                    'config',
                    'bcr_map.yaml'
                ),
                'use_sim_time': use_sim_time,
            }],
        )

        map_lifecycle = Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_map',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': ['map_server'],
            }],
        )

        return robot_groups + [
            map_server,
            map_lifecycle,
        ]

    return LaunchDescription([

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock',
        ),

        DeclareLaunchArgument(
            'robots_config',
            default_value=os.path.join(
                bcr_bot_pkg,
                'config',
                'robots.yaml',
            ),
            description='Path to robots YAML config',
        ),

        OpaqueFunction(
            function=launch_setup
        ),
    ])