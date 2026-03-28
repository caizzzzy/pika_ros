import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np
from functools import partial

class AllCameraSubscriber(Node):
    def __init__(self):
        super().__init__('all_camera_subscriber')
        self.bridge = CvBridge()
        
        # === 1. 定义所有要订阅的 Topic ===
        self.camera_topics = [
            # --- RGB 图像 ---
            '/gripper/camera_l/color/image_raw',
            '/gripper/camera_r/color/image_raw',
            '/gripper/camera_fisheye_l/color/image_raw',
            '/gripper/camera_fisheye_r/color/image_raw',
            '/sensor/camera_l/color/image_raw',
            '/sensor/camera_r/color/image_raw',
            '/sensor/camera_fisheye_l/color/image_raw',
            '/sensor/camera_fisheye_r/color/image_raw',
            
            # --- 深度 图像 (新增) ---
            '/gripper/camera_l/depth/image_raw',
            '/gripper/camera_r/depth/image_raw',
            '/sensor/camera_l/depth/image_raw',
            '/sensor/camera_r/depth/image_raw'
        ]

        # === 2. 批量创建订阅 ===
        self.subscriptions_list = []
        for topic in self.camera_topics:
            callback_function = partial(self.image_callback, topic_name=topic)
            
            # 注意：如果画面很卡，可以将 depth=10 改为 depth=1 (只保留最新一帧)
            # 或者添加 ReliabilityPolicy.BEST_EFFORT
            sub = self.create_subscription(
                Image,
                topic,
                callback_function,
                10 
            )
            self.subscriptions_list.append(sub)
            self.get_logger().info(f'Subscribed to: {topic}')

    def image_callback(self, msg, topic_name):
        try:
            cv_image = None
            
            # === 3. 判断是否为深度图 ===
            if "depth" in topic_name:
                # 深度图处理逻辑
                # 使用 'passthrough' 保持原始数据格式 (通常是 16UC1 或 32FC1)
                depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

                # 处理 NaN 值 (防止程序崩溃)
                depth_image = np.nan_to_num(depth_image, copy=False)

                # --- 可视化关键步骤 ---
                # 将深度值归一化到 0-255 之间以便显示
                # 注意：min/max 可能会根据场景距离剧烈跳动，这里使用简单的 MinMax 归一化
                # 如果你想固定距离范围（例如 0-1米），可以手动指定 vmin, vmax
                norm_image = cv2.normalize(depth_image, None, 0, 255, cv2.NORM_MINMAX)
                
                # 转为 8位 无符号整型
                norm_image = norm_image.astype(np.uint8)
                
                # 应用伪彩色 (COLORMAP_JET: 蓝色近/冷，红色远/热，或者反过来，取决于库版本)
                # 这样比看灰度图更清晰
                cv_image = cv2.applyColorMap(norm_image, cv2.COLORMAP_JET)
                
            else:
                # 普通 RGB 图像处理逻辑
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # === 4. 在图像上绘制 Topic 名称 ===
            # 缩小字体以防遮挡
            cv2.putText(cv_image, topic_name.split('/')[-3] + "/" + topic_name.split('/')[-2], 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # === 5. 显示图像 ===
            # 窗口名使用 Topic 全名
            cv2.imshow(f"View: {topic_name}", cv_image)
            cv2.waitKey(1)

        except CvBridgeError as e:
            self.get_logger().error(f'CvBridge Error: {e}')
        except Exception as e:
            self.get_logger().error(f'Processing Error [{topic_name}]: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = AllCameraSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()