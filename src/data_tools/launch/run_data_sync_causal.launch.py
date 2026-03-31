import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def generate_launch_description():

    share_dir = get_package_share_directory('data_tools')

    declared_arguments = [
        DeclareLaunchArgument('type', default_value='aloha'),
        DeclareLaunchArgument('datasetDir', default_value='/home/agilex/data'),
        DeclareLaunchArgument('episodeIndex', default_value='-1'),
        DeclareLaunchArgument('timeDiffLimit', default_value='0.03'),
        DeclareLaunchArgument('camera_color_policy', default_value='nearest'),
        DeclareLaunchArgument('camera_depth_policy', default_value='nearest'),
        DeclareLaunchArgument('camera_point_cloud_policy', default_value='nearest'),
        DeclareLaunchArgument('arm_joint_state_policy', default_value='causal'),
        DeclareLaunchArgument('arm_end_pose_policy', default_value='causal'),
        DeclareLaunchArgument('localization_pose_policy', default_value='causal'),
        DeclareLaunchArgument('gripper_encoder_policy', default_value='causal'),
        DeclareLaunchArgument('imu_9axis_policy', default_value='causal'),
        DeclareLaunchArgument('lidar_point_cloud_policy', default_value='causal'),
        DeclareLaunchArgument('robot_base_vel_policy', default_value='causal'),
        DeclareLaunchArgument('lift_motor_policy', default_value='causal')
    ]

    type = LaunchConfiguration('type')
    dataset_dir = LaunchConfiguration('datasetDir')
    episode_index = LaunchConfiguration('episodeIndex')
    time_diff_limit = LaunchConfiguration('timeDiffLimit')
    camera_color_policy = LaunchConfiguration('camera_color_policy')
    camera_depth_policy = LaunchConfiguration('camera_depth_policy')
    camera_point_cloud_policy = LaunchConfiguration('camera_point_cloud_policy')
    arm_joint_state_policy = LaunchConfiguration('arm_joint_state_policy')
    arm_end_pose_policy = LaunchConfiguration('arm_end_pose_policy')
    localization_pose_policy = LaunchConfiguration('localization_pose_policy')
    gripper_encoder_policy = LaunchConfiguration('gripper_encoder_policy')
    imu_9axis_policy = LaunchConfiguration('imu_9axis_policy')
    lidar_point_cloud_policy = LaunchConfiguration('lidar_point_cloud_policy')
    robot_base_vel_policy = LaunchConfiguration('robot_base_vel_policy')
    lift_motor_policy = LaunchConfiguration('lift_motor_policy')

    return LaunchDescription(declared_arguments + [
        Node(
            package='data_tools',
            executable='data_tools_dataSyncCausal',
            parameters=[
                [TextSubstitution(text=os.path.join(share_dir, 'config/')), type, TextSubstitution(text='_data_params.yaml')],
                {
                    'episodeIndex': episode_index,
                    'datasetDir': dataset_dir,
                    'timeDiffLimit': time_diff_limit,
                    'sync_policy.camera.color': camera_color_policy,
                    'sync_policy.camera.depth': camera_depth_policy,
                    'sync_policy.camera.pointCloud': camera_point_cloud_policy,
                    'sync_policy.arm.jointState': arm_joint_state_policy,
                    'sync_policy.arm.endPose': arm_end_pose_policy,
                    'sync_policy.localization.pose': localization_pose_policy,
                    'sync_policy.gripper.encoder': gripper_encoder_policy,
                    'sync_policy.imu.9axis': imu_9axis_policy,
                    'sync_policy.lidar.pointCloud': lidar_point_cloud_policy,
                    'sync_policy.robotBase.vel': robot_base_vel_policy,
                    'sync_policy.lift.motor': lift_motor_policy
                }
            ],
            output='screen'
        )
    ])
