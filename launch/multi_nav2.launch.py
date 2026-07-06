#!/usr/bin/env python3

import os
import yaml
import tempfile
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, GroupAction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def launch_setup(context, *args, **kwargs):
    bcr_bot_pkg = get_package_share_directory('bcr_bot')
    
    robots_config = LaunchConfiguration('robots_config').perform(context)
    with open(robots_config, 'r') as f:
        robots = yaml.safe_load(f).get('robots', [])
        
    template_path = os.path.join(bcr_bot_pkg, 'config', 'nav2_template.yaml')
    with open(template_path, 'r') as f:
        template_content = f.read()
        
    use_sim_time = LaunchConfiguration('use_sim_time')
    launch_cmds = []
    

    nav2_nodes = [
        ('nav2_controller', 'controller_server', 'controller_server'),
        ('nav2_planner', 'planner_server', 'planner_server'),
        ('nav2_behaviors', 'behavior_server', 'behavior_server'),
        ('nav2_bt_navigator', 'bt_navigator', 'bt_navigator')
    ]
    
    for index, robot in enumerate(robots):
        ns = robot['name']
        
        robot_yaml_content = template_content.replace('<ROBOT_NAME>', ns)
        fd, dynamic_params_path = tempfile.mkstemp(suffix='.yaml', prefix=f'nav2_params_{ns}_')
        with os.fdopen(fd, 'w') as f:
            f.write(robot_yaml_content)
        
        node_actions = []
        lifecycle_node_names = []
        
        for pkg, exe, name in nav2_nodes:
            lifecycle_node_names.append(name)
            node_actions.append(Node(
                package=pkg,
                executable=exe,
                name=name,
                output='screen',
                parameters=[dynamic_params_path, {'use_sim_time': use_sim_time}],
                remappings=[('map', '/map')]
            ))
        
        node_actions.append(Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[
                {'use_sim_time': use_sim_time},
                {'autostart': True},
                {'node_names': lifecycle_node_names}
            ]
        ))
        
        nav_group = GroupAction([
            PushRosNamespace(ns),
            *node_actions
        ])

        delayed_launch = TimerAction(
            period=5.0 * index, 
            actions=[nav_group]
        )
        
        launch_cmds.append(delayed_launch)
        
    return launch_cmds

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'robots_config', 
            default_value=os.path.join(get_package_share_directory('bcr_bot'), 'config', 'robots.yaml')
        ),
        OpaqueFunction(function=launch_setup)
    ])