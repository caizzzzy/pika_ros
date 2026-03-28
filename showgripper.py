#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

class GripperMonitor(Node):
    def __init__(self):
        super().__init__('gripper_monitor')
        
        # 配置: 这里根据你的 topic list 选择了对应的 joint_state 话题
        self.topic_left = '/sensor/gripper_l/joint_state'
        self.topic_right = '/gripper/gripper_r/joint_state'

        # 订阅左夹爪
        self.subscription_l = self.create_subscription(
            JointState,
            self.topic_left,
            self.left_callback,
            10)
        
        # 订阅右夹爪
        self.subscription_r = self.create_subscription(
            JointState,
            self.topic_right,
            self.right_callback,
            10)
            
        print(f"开始监听夹爪话题:\n 1. {self.topic_left}\n 2. {self.topic_right}")
        print("按 Ctrl+C 退出...")

    def left_callback(self, msg):
        # msg.position 是一个浮点数列表
        # msg.name 通常包含关节名称
        if msg.position:
            # 取第一位数据，通常夹爪只有一个自由度或联动
            val = msg.position[0]
            # \033[92m 是绿色打印，方便区分左右
            print(f"\033[92m[Left ]\033[0m 开合度: {val:.5f} | 原始数据: {msg.position}")

    def right_callback(self, msg):
        if msg.position:
            val = msg.position[0]
            # \033[94m 是蓝色打印
            print(f"\033[94m[Right]\033[0m 开合度: {val:.5f} | 原始数据: {msg.position}")

def main(args=None):
    rclpy.init(args=args)
    monitor = GripperMonitor()
    
    try:
        rclpy.spin(monitor)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()