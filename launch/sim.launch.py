import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_bcr_bot = get_package_share_directory('bcr_bot')

    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Include Gazebo launch
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bcr_bot, 'launch', 'gz.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Include RViz + Robot State Publisher launch
    rviz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_bcr_bot, 'launch', 'rviz.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'isaac_sim': 'true'
        }.items()
    )

    # Foxglove Bridge — launched here so it inherits the sourced workspace
    # and can resolve package:// URIs for mesh assets.
    # The default asset_uri_allowlist regex is too restrictive for paths
    # with subdirectories and file extensions, so we expand it here.
    foxglove_bridge = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        parameters=[{
            'use_sim_time': True,
            'send_buffer_limit': 10000000,
            'asset_uri_allowlist': [
                "^package://(?:[\\-\\w]+/)*[\\-\\w]+\\.(?:dae|fbx|glb|gltf|jpeg|jpg|mtl|obj|png|stl|tif|tiff|urdf|webp|xacro)$"
            ],
        }],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),
        gz_launch,
        rviz_launch,
        foxglove_bridge
    ])
