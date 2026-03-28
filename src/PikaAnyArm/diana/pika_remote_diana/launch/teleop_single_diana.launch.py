import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    right_params = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'right_params.yaml',
        )
    )

    return LaunchDescription([
        Node(
            package='pika_remote_diana',
            executable='teleop_diana',
            name='teleop_right',
            parameters=[
                right_params,     
                {'index_name': '',
                 'robot_ip': '192.168.10.76',
                 'pika_to_arm': [0.0, 0.0, 0.0, 0.0, 1.570796, 0.0],},   
            ],
            output='screen',
        ),
    ])
