# PIKA ROS Project Overview

## 1. 这份文档解决什么问题

`pika_ros` 不是单一节点，而是一套“采集硬件接入 + ROS 2 数据总线 + 数据录制/回放 + 遥操作执行”的组合工程。

对后续开发最重要的结论是：

- 仓库内真正负责“把硬件数据变成 ROS 2 话题”的核心在 `src/sensor_tools`。
- 仓库内真正负责“把在线 ROS 话题落盘、同步、回放”的核心在 `src/data_tools`。
- 仓库内真正负责“把 Pika 位姿转成机械臂控制”的核心在 `src/PikaAnyArm/diana/pika_remote_diana`。
- 6 自由度位姿本身不在本仓库内直接计算；当前工作区通过外部包 `pika_locator` 接入，`pika_locator` 又依赖 `libsurvive` / Lighthouse 定位链路。README 中提到的 `pika_sdk` 是更上游的生态依赖，但本仓库未内置其源码。

## 2. 系统边界与总体结构

### 2.1 仓内主包

- `src/sensor_tools`
  - 采集侧驱动封装。
  - 负责 USB 鱼眼相机、串口 gripper/IMU、Realsense launch 组合。
- `src/data_tools`
  - 数据录制、MCAP 录制、离线同步、离线回放。
- `src/data_msgs`
  - 自定义消息与服务。
- `src/PikaAnyArm/diana/pika_remote_diana`
  - Pika 位姿到 Diana 机械臂控制的 ROS 2 遥操作适配层。
- `src/realsense-ros`
  - vendored 的 RealSense ROS 2 驱动。

### 2.2 仓外但被系统强依赖的部分

- `pika_locator`
  - 当前工作区已安装到 `install/pika_locator`。
  - 提供 `pika_single_locator_node` / `pika_double_locator_node`。
  - 发布 `/pika_pose*` 与 `/pika_localization_status*`。
- `libsurvive`
  - `pika_locator` 通过它接 Lighthouse / Vive 定位链。
  - 现场启动流程里要先跑 `survive-cli` 做基站校准。
- Diana SDK
  - `teleop_diana.py` 通过 `diana_robot` 下发机械臂控制。

### 2.3 目录角色

- `start_pika/`
  - 现场使用的一键启动器，最接近产品手册里的操作流程。
- `scripts/`
  - 根目录辅助脚本，很多与 `src/data_tools/scripts`、`src/sensor_tools/scripts` 作用重合，更偏快捷入口/实验脚本。
- `docs/`
  - 已有项目说明草稿，可作为补充，但当前根目录这份文档更聚焦核心数据流。

## 3. 核心在线数据流

### 3.1 6DoF 空间信息链路

这部分不是本仓库自己解算，而是：

1. 现场先运行 `survive-cli` 完成 Lighthouse / Vive 基站工作。
2. `sensor_tools` 的 launch 再包含 `pika_locator` 的单手或双手 launch。
3. `pika_locator` 节点输出：
   - 单手：`/pika_pose`、`/pika_localization_status`
   - 双手：`/pika_pose_l`、`/pika_pose_r`、`/pika_localization_status_l`、`/pika_localization_status_r`
4. 这些位姿话题再被：
   - `data_tools_dataCapture` 录制
   - `teleop_diana` 订阅并转成机械臂控制

从安装产物和 launch 可以确认：

- `pika_double_locator.launch.py` 暴露了 `publish_rate`，默认 `100.0 Hz`。
- 双手 launch 还要求 `left_hand_code`、`right_hand_code`，说明左右手定位标签需要和现场设备码绑定。
- 单手 launch 没暴露 `publish_rate` 参数，所以单手默认发布频率在仓内不可直接配置；它依赖外部 `pika_single_locator_node` 实现。

### 3.2 深度图 / RGB / 广角图链路

### 深度与窄视角 RGB

- 来源：`realsense2_camera`。
- 由 `sensor_tools` 各 launch 通过 `IncludeLaunchDescription(rs_launch.py)` 拉起。
- 默认 profile 来自 launch 参数 `camera_profile`，默认值是 `640x480x30` 或 `640,480,30`。
- 典型输出话题：
  - `/camera/color/image_raw`
  - `/camera/aligned_depth_to_color/image_raw`
  - `/gripper/camera/color/image_raw`
  - `/gripper/camera/aligned_depth_to_color/image_raw`
  - `/global_camera/color/image_raw`
  - `/global_camera/aligned_depth_to_color/image_raw`

### 广角鱼眼 RGB

- 来源：`src/sensor_tools/scripts/usb_camera.py`
- 节点名通常是 `camera_fisheye`、`camera_fisheye_l`、`camera_fisheye_r`。
- 发布：
  - `.../color/image_raw`
  - `.../color/camera_info`
  - 同时广播一个静态样式 TF：`camera_frame_id -> camera_frame_id_color`
- 默认频率：`camera_fps=30`

### 录制时如何保存相机内参与外参

`data_tools_dataCapture` 不只是存图像，还会：

- 订阅对应 `CameraInfo`
- 从 TF buffer 查 `parentFrame -> msg.frame_id`
- 把相机内参和相机相对父坐标系的位姿一起写到每个相机目录下的 `config.json`

这意味着后处理和回放时不需要再额外猜外参来源。

### 3.3 gripper / IMU / 本地交互链路

`src/sensor_tools/src/serial_gripper_imu.cpp` 是这一段的核心。

### 输入侧

- 通过串口读设备 JSON 包，已确认会解析这些 key：
  - `AS5047`
  - `IMU`
  - `motor`
  - `motorstatus`
  - `Command`

### 输出侧

- `/gripper/data`：`data_msgs/msg/Gripper`
- `/gripper/joint_state`：夹爪开口对应的 `JointState`
- `/imu/data`：`sensor_msgs/msg/Imu`
- `/joint_state_gripper`：把机械臂关节态和 gripper 开口拼到一起后的 `JointState`

### 控制输入

- `/gripper/ctrl`
- `/gripper/joint_state_ctrl`
- `/joint_state_info`

### 状态反馈输入

- `/data_capture_status`
- `/teleop_status`
- `/localization_status`
- `/arm_control_status`

这几个状态不会改变 ROS 数据流本身，但会驱动 Pika 末端设备的灯光/震动反馈。

### 一个很关键的隐藏控制链

串口 JSON 里如果出现 `Command` 字段变化，`serial_gripper_imu` 会主动调用：

- `/teleop_trigger` 服务
- `/data_tools_dataCapture/capture_service` 服务

也就是说，Pika 末端硬件按键可以直接联动：

- 开始/停止 teleop
- 开始/停止数据采集

这条链路是“采集执行一体化”里最关键的人机闭环之一。

### 3.4 在线 ROS 话题到数据集的链路

`data_tools_dataCapture` 的工作方式：

1. 从 YAML 读取要采的 topic 列表。
2. 为每一类模态创建订阅器。
3. 回调里把消息推入 `BlockingDeque`。
4. 每类模态都有独立保存线程，把消息写成：
   - 图像：PNG
   - 位姿/关节/夹爪/IMU：JSON
   - 点云：PCD
5. `monitoring()` 每秒统计一次各 topic 的 `count_in_seconds` 与平均频率。
6. 同时发布 `/data_tools_dataCapture/status`。

默认监控阈值：

- `hz=20`
- `timeout=2`

即：如果某 topic 连续 2 秒低于阈值，会把 `CaptureStatus.fail` 置为 `true`。

### 3.5 在线 ROS 话题到 MCAP 的链路

另一条常用链路是：

1. `compress_camera.py`
   - RGB 编成 JPEG
   - 深度图编成 PNG
2. `record_mcap.py`
   - 订阅压缩后的图像与其他原始 topic
   - 写成 MCAP
   - 也会发布 `/data_tools_dataCapture/status`

这条链路和 `data_tools_dataCapture` 的差别是：

- `data_tools_dataCapture` 产出“目录化原始数据集”
- `record_mcap.py` 产出“单文件/单目录 MCAP”

### 3.6 离线同步与离线回放链路

### 同步

`data_tools_dataSync`

- 输入：各模态目录中的时间戳文件名
- 输出：每个模态目录下的 `sync.txt`
- 默认时间差阈值：`timeDiffLimit=0.03` 秒

### 回放

`data_tools_dataPublish`

- 读取 `sync.txt`
- 按 `publishRate` 节拍依次释放各模态
- 默认 `publishRate=30 Hz`
- 回放时会重新发布图像、深度、点云、位姿、关节、夹爪、IMU、里程计和 TF

## 4. ROS 2 节点与话题地图

### 4.1 采集主节点

| 节点 | 主要订阅 | 主要发布 | 默认节拍/说明 |
| --- | --- | --- | --- |
| `pika_single_locator` | 外部 Lighthouse / libsurvive 数据 | `/pika_pose`, `/pika_localization_status` | 单手频率仓内未显式配置 |
| `pika_double_locator` | 外部 Lighthouse / libsurvive 数据 | `/pika_pose_l`, `/pika_pose_r`, `/pika_localization_status_l`, `/pika_localization_status_r` | `publish_rate=100 Hz` |
| `usb_camera.py` | V4L2 摄像头 | `.../color/image_raw`, `.../color/camera_info` | `30 Hz` 默认 |
| `serial_gripper_imu` | 串口 JSON, `/gripper/ctrl`, `/gripper/joint_state_ctrl`, `/joint_state_info` | `/gripper/data`, `/gripper/joint_state`, `/imu/data`, `/joint_state_gripper` | 串口轮询 `100 Hz`，控制节流 `50 Hz` 默认 |
| `data_tools_dataCapture` | YAML 中列出的所有观测 topic | `/data_tools_dataCapture/status` | 监控线程 `1 Hz`，检查阈值默认 `20 Hz` |
| `record_mcap.py` | YAML 中列出的所有观测 topic | `/data_tools_dataCapture/status` | 监控线程 `1 Hz` |
| `compress_camera.py` | `/<ns>/color/image_raw`, `/<ns>/aligned_depth_to_color/image_raw` | 对应 `/compressed` | 回调驱动，无固定 timer |

### 4.2 遥操作主节点

| 节点 | 主要订阅 | 主要发布 | 作用 |
| --- | --- | --- | --- |
| `teleop_diana` | `/pika_pose{suffix}` | `/joint_states_single_gripper{suffix}`, `/arm_end_pose{suffix}` | 50 Hz 读取当前 Pika 位姿并对 Diana 下发 `sevol_l` |

`teleop_diana` 还暴露：

- `/teleop_trigger{suffix}` 服务

它的逻辑是：

- 第一次触发：进入 takeover，记录当前 Pika 基准位姿
- 持续运行时：计算相对基准位姿增量
- 把增量姿态从 RPY 转成 rotvec
- 通过 Diana SDK 下发笛卡尔增量控制

## 5. 主要 launch / 现场入口

### 5.1 最重要的现场入口

这些脚本最接近产品手册式操作流程：

- `start_pika/start_single_sensor_capture.sh`
- `start_pika/start_multi_sensor_capture.sh`
- `start_pika/start_single_arm_teleop_capture.sh`
- `start_pika/start_dual_arm_teleop_capture.sh`
- `start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh`

它们共同遵循的流程是：

1. 前台启动 `survive-cli`
2. 人工确认基站/定位状态
3. 启动 sensor/gripper/locator
4. 如有 teleop，再启动 `pika_remote_diana`
5. 最后启动 `data_tools` 采集

这和 Pika 产品手册里的现场使用逻辑是一致的：先保证定位，再拉起采集和执行链。

### 5.2 技术层 launch 入口

### `sensor_tools`

- `open_single_sensor.launch.py`
- `open_multi_sensor.launch.py`
- `open_single_gripper.launch.py`
- `open_multi_gripper.launch.py`
- `open_sensor_gripper.launch.py`

### `data_tools`

- `run_data_capture.launch.py`
- `run_data_capture_to_mcap.launch.py`
- `run_multi_data_capture_to_mcap.launch.py`
- `run_data_sync.launch.py`
- `run_data_publish.launch.py`

### `pika_remote_diana`

- `teleop_single_diana.launch.py`
- `teleop_double_diana.launch.py`

## 6. 目录与技术栈边界

### 6.1 C++ 和 Python 的边界

### C++ 为主

- `src/sensor_tools/src/serial_gripper_imu.cpp`
- `src/data_tools/src/dataCapture.cpp`
- `src/data_tools/src/dataSync.cpp`
- `src/data_tools/src/dataPublish.cpp`

这些模块负责：

- 高吞吐 ROS 订阅/发布
- 文件落盘
- 点云/图像处理
- 多线程与队列

### Python 为主

- `src/sensor_tools/scripts/usb_camera.py`
- `src/data_tools/scripts/record_mcap.py`
- `src/data_tools/scripts/compress_camera.py`
- `src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py`

这些模块负责：

- 轻量设备接入
- MCAP 录制
- 图像压缩
- 遥操作适配

### 一个值得注意的现实情况

`src/PikaAnyArm/README.md` 仍写着 Ubuntu 20.04 / ROS Noetic，但当前仓内实际代码已经是 ROS 2 风格：

- `launch.py`
- `rclpy`
- `setup.py console_scripts`

所以后续判断以当前代码实现为准，不要被该 README 的旧环境描述误导。

### 6.2 构建方式

- `sensor_tools` 和 `data_tools`：`ament_cmake`
- `pika_remote_diana`：Python `setup.py`
- 自定义消息：`data_msgs`
- 目标环境：仓库根 README 标的是 Ubuntu 22.04 + ROS 2 Humble

## 7. 后续开发时最该记住的几个点

- `/pika_pose*` 是整个系统最核心的上游总线之一，但它来自外部 `pika_locator`，不在本仓库内解算。
- `serial_gripper_imu` 不只是 gripper 驱动，它还是现场“按键触发 teleop / 采集”的桥。
- `data_tools` 的所有采集/回放 topic 基本都不是写死在代码里，而是从 YAML 配置装配出来的。
- 采集期与回放期的话题集合是一致思路，差别主要在：
  - 采集期从在线 topic 订阅并落盘
  - 回放期从磁盘读 `sync.txt` 再重发
- 如果要新接一个传感器，最稳妥的切入点通常是：
  1. 在 `data_msgs` 定义消息（如有需要）
  2. 在 `sensor_tools` 或独立节点发布 ROS topic
  3. 在 `data_tools/config/*.yaml` 把它接进采集/回放链

## 8. 关键默认频率汇总

| 链路/节点 | 默认频率 |
| --- | --- |
| RealSense 彩色/深度 | `30 Hz`（由 `camera_profile` 默认值决定） |
| USB 鱼眼 `usb_camera.py` | `30 Hz` |
| `pika_double_locator` 位姿发布 | `100 Hz` |
| `teleop_diana` 控制循环、机械臂状态发布 | `50 Hz` |
| `serial_gripper_imu` 控制节流 `ctrl_rate` | `50 Hz` |
| `serial_gripper_imu` 串口轮询 | `100 Hz` |
| `data_tools_dataCapture` 健康监控输出 | `1 Hz` |
| `record_mcap.py` 健康监控输出 | `1 Hz` |
| `data_tools` 默认采集检查阈值 | `20 Hz` |
| `data_tools_dataPublish` 回放节拍 | `30 Hz` |
| `data_tools_dataSync` 默认对齐容差 | `30 ms` |

## 9. 建议把这份文档作为后续问题定位的索引

以后如果要调试某个问题，可以先按下面的方向定位：

- 看不到位姿：先查 `survive-cli` 和 `pika_locator`
- 有位姿但机械臂不动：查 `teleop_trigger*`、`teleop_diana`
- 图像有但没入库：查 `data_tools/config/*.yaml` 和 `data_tools_dataCapture`
- 录制正常但回放缺帧：查 `sync.txt` 和 `timeDiffLimit`
- 夹爪按键没触发采集：查 `serial_gripper_imu` 的 `Command` 分支与服务名 remap
