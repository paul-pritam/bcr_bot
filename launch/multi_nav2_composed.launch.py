#!/usr/bin/env python3

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    OpaqueFunction,
    TimerAction,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LoadComposableNodes, Node, PushRosNamespace
from launch_ros.descriptions import ComposableNode


def _load_robots(robots_config_path):
    import yaml
    with open(robots_config_path, 'r') as f:
        config = yaml.safe_load(f)

    robots = config.get('robots', []) if isinstance(config, dict) else config
    if not isinstance(robots, list) or not robots:
        raise RuntimeError("No robots found in '{}'".format(robots_config_path))
    return robots


def _make_temp_param_file(nav2_template, robot_name):
    content = nav2_template.replace('<ROBOT_NAME>', robot_name)
    fd, path = tempfile.mkstemp(
        prefix='nav2_{}_'.format(robot_name), suffix='.yaml')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


def launch_setup(context, *args, **kwargs):
    pkg_dir = get_package_share_directory('bcr_bot')
    robots_config = LaunchConfiguration('robots_config').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time')

    with open(robots_config, 'r') as f:
        import yaml
        robots = yaml.safe_load(f).get('robots', [])

    template_path = os.path.join(pkg_dir, 'config', 'nav2_template.yaml')
    with open(template_path, 'r') as f:
        template_content = f.read()

    launch_cmds = []
    nav2_nodes = [
        ('nav2_controller', 'nav2_controller::ControllerServer', 'controller_server'),
        ('nav2_planner', 'nav2_planner::PlannerServer', 'planner_server'),
        ('nav2_behaviors', 'behavior_server::BehaviorServer', 'behavior_server'),
        ('nav2_bt_navigator', 'nav2_bt_navigator::BtNavigator', 'bt_navigator'),
    ]

    for index, robot in enumerate(robots):
        ns = robot['name']

        robot_yaml_content = template_content.replace('<ROBOT_NAME>', ns)
        fd, dynamic_params_path = tempfile.mkstemp(
            suffix='.yaml', prefix='nav2_params_{}_'.format(ns))
        with os.fdopen(fd, 'w') as f:
            f.write(robot_yaml_content)

        lifecycle_node_names = [
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator',
        ]

        container = Node(
            package='rclcpp_components',
            executable='component_container_isolated',
            name='nav2_container',
            output='screen',
            parameters=[dynamic_params_path, {'use_sim_time': use_sim_time}],
            remappings=[('map', '/map')],
        )

        composable_descriptions = []
        for pkg, plugin, name in nav2_nodes:
            composable_descriptions.append(
                ComposableNode(
                    package=pkg,
                    plugin=plugin,
                    name=name,
                    parameters=[dynamic_params_path, {'use_sim_time': use_sim_time}],
                    remappings=[('map', '/map')],
                )
            )

        composable_descriptions.append(
            ComposableNode(
                package='nav2_lifecycle_manager',
                plugin='nav2_lifecycle_manager::LifecycleManager',
                name='lifecycle_manager_navigation',
                parameters=[
                    {'use_sim_time': use_sim_time},
                    {'autostart': True},
                    {'node_names': lifecycle_node_names},
                ],
                remappings=[('map', '/map')],
            )
        )

        load_nodes = LoadComposableNodes(
            target_container='{}/nav2_container'.format(ns),
            composable_node_descriptions=composable_descriptions,
        )

        nav_group = GroupAction([
            PushRosNamespace(ns),
            container,
            load_nodes,
        ])

        delayed_launch = TimerAction(
            period=5.0 * index,
            actions=[nav_group]
        )

        launch_cmds.append(delayed_launch)

    return launch_cmds


def generate_launch_description():
    pkg_dir = get_package_share_directory('bcr_bot')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'robots_config',
            default_value=os.path.join(pkg_dir, 'config', 'robots.yaml')),
        OpaqueFunction(function=launch_setup),
    ])
