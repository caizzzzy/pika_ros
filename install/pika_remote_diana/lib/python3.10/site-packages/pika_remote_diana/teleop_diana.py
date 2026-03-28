#!/usr/bin/env python3
import time
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Header
from std_srvs.srv import Trigger
from .transformations import euler_from_quaternion, quaternion_from_euler

from diana_robot.DianaRobot import DianaRobot
from diana_robot.DianaApi import *
from pika_remote_diana.tools import MATHTOOLS


class ArmIK(Node):
    def __init__(self):
        super().__init__('remote_xarm_node')

        # Declare parameters for ROS2 overrides
        self.declare_parameter('index_name', "")
        self.declare_parameter('robot_ip', "192.168.31.76")
        self.declare_parameter('pika_to_arm', [0.0, 0.0, 0.0, 0.0, 1.570796, 0.0])

        self.index_name = self.get_parameter('index_name').value
        self.robot_ip = self.get_parameter('robot_ip').value
        self.pika_to_arm = list(self.get_parameter('pika_to_arm').value)

        self.tools = MATHTOOLS()
        self.diana_control = DianaRobot(self.robot_ip)

        self.initial_pose_rotvec = self.diana_control.get_tcp_pose()

        temp_rotvec = [
            self.initial_pose_rotvec[3],
            self.initial_pose_rotvec[4],
            self.initial_pose_rotvec[5],
        ]

        roll, pitch, yaw = self.tools.rotvec_to_rpy(temp_rotvec)
        self.initial_pose_rpy = self.initial_pose_rotvec[:]
        self.initial_pose_rpy[3] = roll
        self.initial_pose_rpy[4] = pitch
        self.initial_pose_rpy[5] = yaw

        self.takeover = False
        self.flag = False

        # 单机械臂的初始位置
        self.base_pose = self.initial_pose_rpy

        time.sleep(2)

        # 防止启动时 pika_pose 为空
        self.x, self.y, self.z = (
            self.initial_pose_rpy[0],
            self.initial_pose_rpy[1],
            self.initial_pose_rpy[2],
        )
        self.roll, self.pitch, self.yaw = (
            self.initial_pose_rpy[3],
            self.initial_pose_rpy[4],
            self.initial_pose_rpy[5],
        )

        self._init_ros_interfaces()

    def handle_trigger(self, request, response):
        self.get_logger().info("Service /trigger called")
        self.takeover = not self.takeover
        self.get_logger().info(f"反转 {self.takeover}")

        if self.takeover:
            self.base_pose = [self.x, self.y, self.z, self.roll, self.pitch, self.yaw]
            self.flag = True
            self.get_logger().info("开始遥操作")
        else:
            self.flag = False
            # 遥操结束机械臂停止在当前位姿，下次遥操从当前位置开始
            self.diana_control.wait_move()
            ret = changeControlMode(mode_e.T_MODE_POSITION, self.robot_ip)
            # self.diana_control.movej_joint(np.array([-45, -30, 0, 120, 0, -60, 45])*np.pi/180)
            self.diana_control.wait_move()
            self.initial_pose_rotvec = self.diana_control.get_tcp_pose()
            temp_rotvec = [
                self.initial_pose_rotvec[3],
                self.initial_pose_rotvec[4],
                self.initial_pose_rotvec[5],
            ]
            roll, pitch, yaw = self.tools.rotvec_to_rpy(temp_rotvec)
            self.initial_pose_rpy = self.initial_pose_rotvec[:]
            self.initial_pose_rpy[3] = roll
            self.initial_pose_rpy[4] = pitch
            self.initial_pose_rpy[5] = yaw
            self.base_pose = self.initial_pose_rpy
            ret = changeControlMode(mode_e.T_MODE_CART_IMPEDANCE, self.robot_ip)
            self.get_logger().info("停止遥操")
            

        response.success = True
        response.message = "Triggered successfully"
        return response

    # 增量式控制
    def calc_pose_incre(self, base_pose, pose_data):
        begin_matrix = self.tools.xyzrpy2Mat(
            base_pose[0],
            base_pose[1],
            base_pose[2],
            base_pose[3],
            base_pose[4],
            base_pose[5],
        )
        zero_matrix = self.tools.xyzrpy2Mat(
            self.initial_pose_rpy[0],
            self.initial_pose_rpy[1],
            self.initial_pose_rpy[2],
            self.initial_pose_rpy[3],
            self.initial_pose_rpy[4],
            self.initial_pose_rpy[5],
        )
        end_matrix = self.tools.xyzrpy2Mat(
            pose_data[0],
            pose_data[1],
            pose_data[2],
            pose_data[3],
            pose_data[4],
            pose_data[5],
        )
        result_matrix = np.dot(zero_matrix, np.dot(np.linalg.inv(begin_matrix), end_matrix))
        return self.tools.mat2xyzrpy(result_matrix)

    # 订阅 pika_pose 回调函数
    def pose_callback(self, msg: PoseStamped):
        x = msg.pose.position.x
        y = msg.pose.position.y
        z = msg.pose.position.z
        roll, pitch, yaw = euler_from_quaternion(
            [
                msg.pose.orientation.x,
                msg.pose.orientation.y,
                msg.pose.orientation.z,
                msg.pose.orientation.w,
            ]
        )
        self.x, self.y, self.z, self.roll, self.pitch, self.yaw = self.adjustment(
            x, y, z, roll, pitch, yaw
        )

    # 调整矩阵函数
    def adjustment(self, x, y, z, Rx, Ry, Rz):
        transform = self.tools.xyzrpy2Mat(x, y, z, Rx, Ry, Rz)

        # 调整坐标轴方向  pika--->机械臂末端
        r_adj = self.tools.xyzrpy2Mat(
            self.pika_to_arm[0],
            self.pika_to_arm[1],
            self.pika_to_arm[2],
            self.pika_to_arm[3],
            self.pika_to_arm[4],
            self.pika_to_arm[5],
        )

        transform = np.dot(transform, r_adj)
        x_, y_, z_, Rx_, Ry_, Rz_ = self.tools.mat2xyzrpy(transform)
        return x_, y_, z_, Rx_, Ry_, Rz_

    def _init_ros_interfaces(self):
        qos = QoSProfile(depth=1)
        self.pose_sub = self.create_subscription(
            PoseStamped,
            f'/pika_pose{self.index_name}',
            self.pose_callback,
            qos,
        )
        self.trigger_srv = self.create_service(
            Trigger,
            f'/teleop_trigger{self.index_name}',
            self.handle_trigger,
        )

        self.joint_pub = self.create_publisher(
            JointState, f'/joint_states_single_gripper{self.index_name}', qos
        )
        self.end_pose_pub = self.create_publisher(
            PoseStamped, f'/arm_end_pose{self.index_name}', qos
        )

        # 50 Hz timer loop for main control
        self.control_timer = self.create_timer(1.0 / 50.0, self._loop_once)

    def _loop_once(self):
        # 获取并发布关节状态
        try:
            current_joints = self.diana_control.getjoints()
            if current_joints:
                joint_msg = JointState()
                joint_msg.header = Header()
                joint_msg.header.stamp = self.get_clock().now().to_msg()
                joint_msg.name = [f'joint{i}' for i in range(len(current_joints))]
                joint_msg.position = current_joints
                self.joint_pub.publish(joint_msg)
        except Exception:
            pass

        # 获取并发布末端位姿 (EndPose)
        try:
            tcp_pose = self.diana_control.get_tcp_pose()
            if tcp_pose:
                pose_msg = PoseStamped()
                pose_msg.header = Header()
                pose_msg.header.stamp = self.get_clock().now().to_msg()
                pose_msg.header.frame_id = "base_link"

                pose_msg.pose.position.x = tcp_pose[0]
                pose_msg.pose.position.y = tcp_pose[1]
                pose_msg.pose.position.z = tcp_pose[2]

                roll, pitch, yaw = self.tools.rotvec_to_rpy(tcp_pose[3:6])
                q = quaternion_from_euler(roll, pitch, yaw)

                pose_msg.pose.orientation.x = q[0]
                pose_msg.pose.orientation.y = q[1]
                pose_msg.pose.orientation.z = q[2]
                pose_msg.pose.orientation.w = q[3]

                self.end_pose_pub.publish(pose_msg)
        except Exception:
            pass

        current_pose = [self.x, self.y, self.z, self.roll, self.pitch, self.yaw]
        increment_pose = self.calc_pose_incre(self.base_pose, current_pose)

        rotvec_pose = self.tools.rpy_to_rotvec(
            increment_pose[3], increment_pose[4], increment_pose[5]
        )
        increment_pose[3:6] = rotvec_pose

        # 下发 pose 至机械臂
        if self.flag:
            self.diana_control.sevol_l(increment_pose)


def main(args=None):
    rclpy.init(args=args)
    node = ArmIK()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("程序已退出")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
