from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='pika_remote_diana',
            executable='teleop_diana',   # setup.py 里定义的 entry point
            name='teleop_left',
            parameters=[{
                'index_name': '_l',
                'robot_ip': '192.168.10.75',
                'pika_to_arm': [0.0, 0.0, 0.0, 0.0, 1.570796, 0.0],
            }],
            output='screen',
        ),
        Node(
            package='pika_remote_diana',
            executable='teleop_diana',
            name='teleop_right',
            parameters=[{
                'index_name': '_r',
                'robot_ip': '192.168.10.76',
                'pika_to_arm': [0.0, 0.0, 0.0, 0.0, 1.570796, 0.0],
            }],
            output='screen',
        ),
    ])
