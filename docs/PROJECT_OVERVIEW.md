# PROJECT OVERVIEW

## 1. 项目目标

- 已确认：`pika_ros` 是一个 ROS 2 Humble 项目，围绕 Pika 采集设备构建，核心职责分成三类：
  - 传感器与末端执行器接入 ROS
  - 多模态数据采集、时间同步、回放、MCAP 录制
  - 将 `pika_pose` 一类空间观测转换成机械臂遥操作控制
- 已确认：仓库本身不是完整机器人业务栈，更像“设备接入 + 数据工具 + 遥操作适配层”。
- 已确认：主要面向以下场景：
  - 单 Pika / 双 Pika 采集
  - 带夹爪与相机的 teleop 数据采集
  - 采集数据离线同步与回放
  - Pika 到 Diana 机械臂的实时遥操作
- 推测：`source/`、根目录若干脚本和 `scripts/` 下的 Python 脚本更多用于实验、调试、格式转换，不是稳定主入口。

## 2. 系统组成总览

### 软件组成

- `src/data_tools`
  - 已确认：数据采集、时间同步、离线回放、MCAP 录制、图像压缩。
- `src/sensor_tools`
  - 已确认：USB 鱼眼相机接入、串口夹爪/IMU 接入、单/双设备 launch 组织。
- `src/PikaAnyArm/diana/pika_remote_diana`
  - 已确认：把 `/pika_pose*` 转成 Diana 机械臂末端笛卡尔增量控制。
- `src/data_msgs`
  - 已确认：采集状态、夹爪状态、自定义服务的消息定义。
- `src/realsense-ros`
  - 已确认：RealSense ROS 2 驱动源码，供 depth camera launch 引用。

### 硬件组成

- 从代码已确认：
  - RealSense 深度相机
  - USB 鱼眼相机
  - 带编码器与 IMU 的夹爪/手持端，走串口通信
  - Pika 定位/位姿来源，依赖外部 `pika_locator` 包
  - 可选 Diana 机械臂，走 Diana SDK
  - 某些配置下还有移动底盘 odom、升降机构 lift 电机状态
- 从外部手册镜像可确认：
  - Pika 方案包含采集装置、定位基站、定位标签、数据背包/工控机
  - 单/双手配置要区分左右手 USB 口、鱼眼相机口、深度相机序列号、定位标签编码
  - 夹爪电气连接使用 24V 供电，通信/控制走 Type-C/USB
- 需结合设备文档确认：
  - Pika 本体内部各传感器的精确型号
  - 定位基站/标签的坐标系定义与精度边界
  - 各夹爪相机到夹爪中心的标定参数来源

### 各部分关系

- 观测链：
  - RealSense / USB 鱼眼 / 串口夹爪+IMU / `pika_locator` -> ROS topics
- 数据链：
  - ROS topics -> `data_tools_dataCapture` 或 `record_mcap.py` -> episode 目录 / MCAP
  - episode 目录 -> `data_tools_dataSync` -> `sync.txt`
  - episode 目录 + `sync.txt` -> `data_tools_dataPublish` -> 重放 ROS topics
- 控制链：
  - `pika_locator` 输出 `pika_pose`
  - `teleop_diana` 将位姿变换到机械臂末端坐标
  - Diana SDK 下发实时末端控制
- 人机状态链：
  - `data_tools_dataCapture/status`、`teleop_status`、`localization_status`、`arm_control_status`
  - -> `serial_gripper_imu`
  - -> 控制夹爪设备上的灯光/震动反馈

## 3. ROS 架构

### 核心节点总表

- `data_tools_dataCapture`
  - 文件：[src/data_tools/src/dataCapture.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataCapture.cpp)
  - 输入：多路传感器 topic、TF
  - 输出：
    - `/data_tools_dataCapture/status`
    - episode 目录下的图片/点云/JSON/config/statistics/instructions
    - 可选 service `/data_tools_dataCapture/capture_service`
  - 功能：采集、监控频率、保存原始数据。

- `data_tools_dataSync`
  - 文件：[src/data_tools/src/dataSync.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataSync.cpp)
  - 输入：episode 目录已有文件
  - 输出：各模态目录下 `sync.txt`
  - 功能：按时间戳做离线对齐，筛出可同步帧。

- `data_tools_dataPublish`
  - 文件：[src/data_tools/src/dataPublish.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataPublish.cpp)
  - 输入：episode 目录 + `sync.txt`
  - 输出：重放后的 image / camera_info / point cloud / joint / pose / gripper / imu / odom / tf
  - 功能：离线数据回放。

- `record_mcap.py`
  - 文件：[src/data_tools/scripts/record_mcap.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/scripts/record_mcap.py)
  - 输入：YAML 指定的话题集合
  - 输出：MCAP 文件夹、`/data_tools_dataCapture/status`
  - 功能：直接订阅线上话题并录成 MCAP；支持 service 触发开始/停止。

- `compress_camera.py`
  - 文件：[src/data_tools/scripts/compress_camera.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/scripts/compress_camera.py)
  - 输入：`/<ns>/color/image_raw`、`/<ns>/aligned_depth_to_color/image_raw`
  - 输出：对应 `/compressed`
  - 功能：给 MCAP 录制提供压缩图像流。

- `serial_gripper_imu`
  - 文件：[src/sensor_tools/src/serial_gripper_imu.cpp](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/src/serial_gripper_imu.cpp)
  - 输入：
    - `/gripper/ctrl`
    - `/gripper/joint_state_ctrl`
    - `/joint_state_info`
    - `/data_capture_status`
    - `/teleop_status`
    - `/localization_status`
    - `/arm_control_status`
  - 输出：
    - `/gripper/data`
    - `/gripper/joint_state`
    - `/imu/data`
    - `/joint_state_gripper`
  - 功能：串口收发夹爪/IMU数据，执行夹爪控制，并把状态映射到灯光/震动提示。

- `usb_camera.py`
  - 文件：[src/sensor_tools/scripts/usb_camera.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/usb_camera.py)
  - 输入：Linux V4L2 摄像头设备
  - 输出：
    - `/camera_rgb/color/image_raw`
    - `/camera_rgb/color/camera_info`
    - 对应静态 TF（`camera_frame_id` -> `camera_frame_id_color`）
  - 功能：鱼眼相机采集。

- `teleop_diana`
  - 文件：[src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py)
  - 输入：
    - `/pika_pose{index_name}`
    - service `/teleop_trigger{index_name}`
  - 输出：
    - `/joint_states_single_gripper{index_name}`
    - `/arm_end_pose{index_name}`
    - Diana SDK 实时运动命令
  - 功能：Pika 位姿到 Diana 机械臂末端增量控制。

### 主要 launch 关系

- 传感器启动
  - 单夹爪：[src/sensor_tools/launch/open_single_gripper.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_single_gripper.launch.py)
  - 单传感器：[src/sensor_tools/launch/open_single_sensor.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_single_sensor.launch.py)
  - 双传感器：[src/sensor_tools/launch/open_multi_sensor.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_multi_sensor.launch.py)
  - 双夹爪：[src/sensor_tools/launch/open_multi_gripper.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_multi_gripper.launch.py)
  - 共同模式：启动 `realsense2_camera` + `usb_camera.py` + `serial_gripper_imu`，并依赖外部 `pika_locator`。

- 数据采集
  - 原始 episode 采集：[src/data_tools/launch/run_data_capture.launch.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/launch/run_data_capture.launch.py)
  - MCAP 采集：[src/data_tools/launch/run_data_capture_to_mcap.launch.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/launch/run_data_capture_to_mcap.launch.py)
  - 变体：
    - `run_aloha_data_capture_to_mcap.launch.py`
    - `run_multi_data_capture_to_mcap.launch.py`
    - `run_lift_data_capture_to_mcap.launch.py`

- 数据处理与回放
  - 同步：[src/data_tools/launch/run_data_sync.launch.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/launch/run_data_sync.launch.py)
  - 回放：[src/data_tools/launch/run_data_publish.launch.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/launch/run_data_publish.launch.py)

- 遥操作
  - 单 Diana：[src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_single_diana.launch.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_single_diana.launch.py)
  - 双 Diana：[src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_double_diana.launch.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_double_diana.launch.py)

## 4. 数据流

### 链路 A：线上传感器 -> episode 原始数据

- observation / sensor input
  - RealSense 彩色、深度
  - USB 鱼眼彩色
  - `pika_locator` 输出位姿 `/pika_pose*`
  - 串口夹爪编码器与 IMU `/gripper*/data`、`/imu*/data`
  - 可选底盘 `/ranger_base_node/odom`
  - 可选升降机构 `/lifter_1/LiftMotorStatePub`
- processing
  - `data_tools_dataCapture` 根据 YAML 注册订阅
  - 各回调把消息放入 `BlockingDeque`
  - 独立保存线程把消息写成图片/点云/JSON
  - 相机类消息会额外保存 `CameraInfo` 和 TF 关系
  - `monitoring()` 每秒计算每个 topic 的 `count_in_seconds` 与 `frequency`
- command / control output
  - 无运动控制输出
  - 输出为 episode 目录内容与 `/data_tools_dataCapture/status`

### 链路 B：线上传感器 -> MCAP

- observation / sensor input
  - 与上面类似，但依赖 `paramsFile` 指定话题
- processing
  - `compress_camera.py` 先把 RGB 编码为 JPEG、深度编码为 PNG
  - `record_mcap.py` 订阅压缩后的图像与其他原始 topic
  - 根据 `useTopicStamp` 选择 topic 原始时间或本地接收时间写入 MCAP
- command / control output
  - MCAP 文件夹
  - `/data_tools_dataCapture/status`

### 链路 C：episode 原始数据 -> 对齐后的可回放数据

- observation / sensor input
  - `episode*/...` 下各类文件名时间戳
- processing
  - `data_tools_dataSync` 扫描各模态目录
  - 以 `allTimeSeries` 为基准推进
  - 对每一类启用 `toSyncs=true` 的模态寻找最接近时间戳
  - 若最近样本与目标帧时间差超过 `timeDiffLimit`，该帧丢弃
  - 通过的样本写入各自 `sync.txt`
- command / control output
  - `sync.txt`

### 链路 D：`pika_pose` -> Diana 机械臂控制

- observation / sensor input
  - `/pika_pose{index_name}`，消息类型 `PoseStamped`
- processing
  - `teleop_diana` 将四元数转 RPY
  - 用参数 `pika_to_arm` 做姿态/坐标修正
  - `calc_pose_incre()` 计算相对 `base_pose` 的增量
  - 增量姿态再转 rotvec
  - 50 Hz 定时器里持续获取机器人当前 joints 和 TCP pose，并在 `flag=True` 时下发 `sevol_l`
- command / control output
  - Diana SDK 实时末端笛卡尔控制
  - ROS 输出机械臂关节与末端位姿用于记录或观察

### 链路 E：状态 -> 人机反馈

- observation / sensor input
  - `/data_tools_dataCapture/status`
  - `/teleop_status`
  - `/localization_status`
  - `/arm_control_status`
- processing
  - `serial_gripper_imu` 回调中更新颜色状态与振动状态
- command / control output
  - 串口下发灯光命令 `LIGHT_CTRL`
  - 串口下发振动命令 `VIBRATE_CTRL`

## 5. 控制逻辑

### 夹爪控制

- 已确认：`serial_gripper_imu` 支持两种控制输入：
  - `data_msgs/Gripper` 直接控制 `/gripper/ctrl`
  - `sensor_msgs/JointState` 间接控制 `/gripper/joint_state_ctrl`
- 已确认：核心控制量包括：
  - `enable`
  - `set_zero`
  - `effort`
  - `velocity`
  - `angle` 或 `distance`
- 已确认：节点会把 `distance` 映射为内部电机角度 `angle`，并做限幅：
  - `distance` 限幅到 `0 ~ 0.098`
  - `angle` 限幅到 `0 ~ 1.67`
- 已确认：控制频率受 `ctrl_rate` 限制，代码中按 `ctrlFreq = 1 / ctrl_rate` 做节流。
- 已确认：实际串口命令包括 `ENABLE`、`DISABLE`、`SET_ZERO`、`VELOCITY_CTRL`、`EFFORT_CTRL`、`POSITION_CTRL_MIT`、`POSITION_CTRL_POS_VEL`。
- 需结合设备文档确认：
  - `angle`、`distance` 单位定义是否分别为 rad / m
  - `effort` 和 `velocity` 的真实物理单位
  - `MIT` 模式与 `POS_VEL` 模式的控制差异和安全边界

### 机械臂控制

- 已确认：Diana 遥操作不是关节级控制，而是末端位姿增量控制。
- 已确认：服务 `/teleop_trigger*` 负责切换 takeover 状态。
- 已确认：关闭遥操作时会调用：
  - `wait_move()`
  - `changeControlMode(T_MODE_POSITION)`
  - 重新读取当前 TCP pose
  - `changeControlMode(T_MODE_CART_IMPEDANCE)`
- 已确认：真正的控制下发在 50 Hz 定时器中调用 `DianaRobot.sevol_l(increment_pose)`。
- 推测：这里依赖 Diana 控制器内部阻抗/伺服实现，仓库本身没有更深的闭环控制。

### 数据采集监控

- 已确认：`data_tools_dataCapture` 每秒统计 topic 帧数和平均频率。
- 已确认：若某 topic 连续超过 `timeout` 秒低于设定 `hz`，则 `captureStatus.fail = true`，采集中止或等待 end signal。
- 已确认：对于 `armJointState` 还额外检查“是否变化”，不变化会报警但不一定立刻退出。

## 6. 关键模块

### `src/` 中最重要的文件

- [src/data_tools/include/dataUtility.h](/mnt/nas/projects/robot/pika_ros/src/data_tools/include/dataUtility.h)
  - 重要原因：整个数据链的“元配置中心”。所有模态的名字、topic、frame、目录、同步开关、回放开关都从这里统一装载。

- [src/data_tools/src/dataCapture.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataCapture.cpp)
  - 重要原因：线上数据进入磁盘的主入口；后续 debug 采集异常、丢帧、目录结构错误都要从这里看。

- [src/data_tools/src/dataSync.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataSync.cpp)
  - 重要原因：决定 episode 是否能形成“对齐后的训练样本”；数据错位首先查这里。

- [src/data_tools/src/dataPublish.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataPublish.cpp)
  - 重要原因：离线回放的唯一主逻辑；回放失真、frame_id 异常、topic 不一致先查这里。

- [src/sensor_tools/src/serial_gripper_imu.cpp](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/src/serial_gripper_imu.cpp)
  - 重要原因：夹爪控制、编码器反馈、IMU、灯振交互都在一个节点里；运动异常和状态提示异常都高度相关。

- [src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py)
  - 重要原因：`pika_pose` 到 Diana 的唯一控制桥。

### `scripts/` 入口脚本

- [src/data_tools/scripts/record_mcap.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/scripts/record_mcap.py)
  - MCAP 采集入口。
- [src/data_tools/scripts/compress_camera.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/scripts/compress_camera.py)
  - 给 MCAP 提供压缩图像输入。
- [src/sensor_tools/scripts/usb_camera.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/usb_camera.py)
  - USB 鱼眼入口。
- [src/sensor_tools/scripts/find_usb_camera.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/find_usb_camera.py)
  - 用于找摄像头口，和外部手册中的设备绑定流程一致。
- [scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/scripts/setup_device.py)
  - 交互式设备绑定生成工具，不是运行期核心节点。
  - 功能概括：
    - 逐个要求用户插入设备，读取 RealSense 序列号、串口 USB 路径、鱼眼摄像头 USB 路径。
    - 根据用户选择的设备组合，生成 `setup_multi_sensor.bash`、`setup_multi_gripper.bash` 或 `setup_sensor_gripper.bash`，以及对应的 `start_*.bash`。
    - 生成的 `setup_*.bash` 会写入 `/etc/udev/rules.d/`，把设备固定绑定到 `ttyUSB50/51/60/61`、`video50/51/60/61` 这套命名。
    - 生成的 `start_*.bash` 会把探测到的 RealSense 序列号和固定端口号写死为启动参数，后续日常运行主要依赖这些生成物，而不是再次运行 `setup_device.py`。
    - 脚本最后会立即执行生成出的 `setup_*.bash`，然后要求用户重新拔插设备，检查绑定是否生效。
  - 适用时机：
    - 首次给新设备做 USB 口/串口/鱼眼绑定。
    - 更换设备或更换插口后重新生成绑定脚本。
  - 不适用时机：
    - 日常 teleop / 采集启动；那时通常直接运行现成的 `start_*.bash` 或 `start_pika/` 下的一键启动器。
  - 代码现状：
    - 仓库在 [src/sensor_tools/scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/setup_device.py) 下还有一份同内容副本，当前看起来是同步拷贝，而不是两套不同逻辑。
  - 当前支持的绑定模式与生成物关系：
    - `1. 两个 pika sensor`
      - 生成 `setup_multi_sensor.bash`
      - 生成 `start_multi_sensor.bash`
      - 绑定结果：`ttyUSB50/51`、`video50/51`
    - `2. 两个 pika gripper`
      - 生成 `setup_multi_gripper.bash`
      - 生成 `start_multi_gripper.bash`
      - 绑定结果：`ttyUSB60/61`、`video60/61`
    - `3. 一个 pika sensor + 一个 pika gripper`
      - 生成 `setup_sensor_gripper.bash`
      - 生成 `start_sensor_gripper.bash`
      - 绑定结果：sensor -> `ttyUSB50/video50`，gripper -> `ttyUSB60/video60`
    - `4. 一个 pika sensor + 两个 pika gripper，其中第二个 gripper 作为 global_camera`
      - 生成 `setup_sensor_2grippers_global_camera.bash`
      - 生成 `start_sensor_2grippers_global_camera.bash`
      - 生成 `start_pika/single_arm_sensor_2grippers_device_config.bash`
      - 绑定结果：sensor -> `ttyUSB50/video50`，gripper_A -> `ttyUSB60/video60`，gripper_B -> `ttyUSB61/video61`
      - 用途说明：
        - `start_sensor_2grippers_global_camera.bash` 只是进入 [start_single_arm_teleop_capture_sensor_2grippers.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh) 的快捷包装。
        - 真正给单臂遥操作启动器提供现场参数的是 `start_pika/single_arm_sensor_2grippers_device_config.bash`，其中会写入 `SENSOR_DEPTH_CAMERA_NO`、`GRIPPER_A_DEPTH_CAMERA_NO`、`GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO` 等变量。
- 根目录脚本
  - [teleop_single_diana.sh](/mnt/nas/projects/robot/pika_ros/teleop_single_diana.sh)
  - [teleop_dual_diana.sh](/mnt/nas/projects/robot/pika_ros/teleop_dual_diana.sh)
  - [promax/init_pika.sh](/mnt/nas/projects/robot/pika_ros/promax/init_pika.sh)
  - 推测：这些是集成环境下的快捷启动壳脚本，不是核心逻辑实现。

### `source/` 的作用

- 已确认不足：仓库当前未扫描到 `source/` 内核心代码入口。
- 推测：更像环境脚本或外部资源目录。
- 建议：后续如果 debug 卡在部署流程，再补读该目录。

### `launch/`、`config/`、`msg/`、`srv/`

- `launch/`
  - 重要原因：决定“这次系统到底起了哪些节点、用了哪套命名空间、单手还是双手、是否带 global camera”。
- `config/*.yaml`
  - 重要原因：决定数据链路中的模态清单、topic 名称、父坐标系、同步/回放开关。
- `msg/`
  - [src/data_msgs/msg/Gripper.msg](/mnt/nas/projects/robot/pika_ros/src/data_msgs/msg/Gripper.msg)
    - 重要原因：夹爪控制和反馈都靠它，字段语义直接影响单位理解。
  - [src/data_msgs/msg/CaptureStatus.msg](/mnt/nas/projects/robot/pika_ros/src/data_msgs/msg/CaptureStatus.msg)
    - 重要原因：采集状态监控和人机反馈依赖它。
- `srv/`
  - [src/data_msgs/srv/CaptureService.srv](/mnt/nas/projects/robot/pika_ros/src/data_msgs/srv/CaptureService.srv)
    - 重要原因：外部 UI / 控制器若要远程启停采集，就走这里。

## 7. 配置与启动方式

### 启动系统的常见顺序

1. 启动传感器侧
   - 单套：`open_single_sensor.launch.py` 或 `open_single_gripper.launch.py`
   - 双套：`open_multi_sensor.launch.py` 或 `open_multi_gripper.launch.py`
   - 如果是新设备首次上机，通常先运行 `scripts/setup_device.py` 生成/刷新 `setup_*.bash` 与 `start_*.bash`，完成 udev 绑定，再进入后续日常启动流程。
2. 确认 `pika_locator` 正常输出 `pika_pose*`
3. 如果需要遥操作，再启动 `teleop_single_diana.launch.py` 或 `teleop_double_diana.launch.py`
4. 如果需要采集：
   - 原始 episode：`run_data_capture.launch.py`
   - MCAP：`run_*_data_capture_to_mcap.launch.py`
5. 采集完成后：
   - 原始 episode 走 `run_data_sync.launch.py`
   - 回放走 `run_data_publish.launch.py`

### 特定场景：1 sensor + 2 grippers，其中 gripper_B 作为 global_camera

- 当前仓库已支持通过 [start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh) 启动该场景。
- 角色分配：
  - `sensor + gripper_A`：单臂遥操作链路
  - `gripper_B`：不参与夹爪控制，只把其深度相机作为 `/global_camera/*` 数据源
- 该模式下，能从当前代码明确确认的关键 topic 如下：
  - teleop 输入与状态
    - `/pika_pose`
    - `/joint_states`
    - `/joint_states_single`
    - `/joint_states_single_gripper`
    - `/arm_end_pose`
  - sensor 侧 gripper/imu
    - `/sensor/gripper/data`
    - `/sensor/gripper/ctrl`
    - `/sensor/gripper/joint_state`
    - `/sensor/imu/data`
  - gripper_A 侧 gripper/imu
    - `/gripper/gripper/data`
    - `/gripper/gripper/ctrl`
    - `/gripper/gripper/joint_state`
    - `/imu/data`
  - 相机话题
    - `/gripper/camera/color/image_raw`
    - `/gripper/camera/color/camera_info`
    - `/gripper/camera/aligned_depth_to_color/image_raw`
    - `/gripper/camera/aligned_depth_to_color/camera_info`
    - `/gripper/camera_fisheye/color/image_raw`
    - `/gripper/camera_fisheye/color/camera_info`
    - `/global_camera/color/image_raw`
    - `/global_camera/color/camera_info`
    - `/global_camera/aligned_depth_to_color/image_raw`
    - `/global_camera/aligned_depth_to_color/camera_info`
- 说明：
  - 这里的 `/global_camera/*` 在该模式下来自 gripper_B 的深度相机序列号，而不是默认外部 RealSense。
  - 当前实现没有把 gripper_B 作为第二套串口夹爪节点单独启动，因此不会额外出现一整套“gripper_B 控制链” topic；它主要以 `/global_camera/*` 这组相机 topic 的形式出现。

### 关键命令形态

- 传感器
  - `ros2 launch sensor_tools open_single_gripper.launch.py`
  - `ros2 launch sensor_tools open_multi_gripper.launch.py`
- 采集
  - `ros2 launch data_tools run_data_capture.launch.py type:=single_pika_teleop datasetDir:=... episodeIndex:=0`
  - `ros2 launch data_tools run_data_capture_to_mcap.launch.py paramsFile:=...`
- 同步
  - `ros2 launch data_tools run_data_sync.launch.py type:=single_pika_teleop datasetDir:=... episodeIndex:=0`
- 回放
  - `ros2 launch data_tools run_data_publish.launch.py type:=single_pika_teleop datasetDir:=... episodeIndex:=0`
- 遥操作
  - `ros2 launch pika_remote_diana teleop_single_diana.launch.py`

### 关键配置文件

- 单 Pika 采集：[src/data_tools/config/single_pika_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/single_pika_data_params.yaml)
- 单 Pika teleop：[src/data_tools/config/single_pika_teleop_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/single_pika_teleop_data_params.yaml)
- 双 Pika 采集：[src/data_tools/config/multi_pika_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/multi_pika_data_params.yaml)
- 双 Pika teleop：[src/data_tools/config/multi_pika_teleop_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/multi_pika_teleop_data_params.yaml)
- Diana 参数：
  - [src/PikaAnyArm/diana/pika_remote_diana/config/right_params.yaml](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/config/right_params.yaml)
  - [src/PikaAnyArm/diana/pika_remote_diana/config/left_params.yaml](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/config/left_params.yaml)

### 最重要参数

- `type`
  - 选择哪套数据模态配置。
- `datasetDir` / `episodeIndex`
  - 决定数据落盘与回放目录。
- `hz` / `timeout`
  - 决定采集时的频率监控容忍度。
- `timeDiffLimit`
  - 决定同步对齐容忍窗口。
- `publishRate`
  - 决定回放速度。
- `camera_profile` / `camera_fps` / `camera_width` / `camera_height`
  - 决定 RealSense / 鱼眼相机输出规格。
- `serial_port` / `camera_port` / `serial_no`
  - 决定硬件设备绑定。
- `robot_ip` / `pika_to_arm`
  - 决定 Diana 遥操作目标与坐标修正。

## 8. 通信与接口

### ROS 内部接口

- Topic
  - 传感器、位姿、夹爪、IMU、odom、状态、回放数据都走 topic。
- Service
  - `/data_tools_dataCapture/capture_service`
  - `/teleop_trigger{index_name}`
- TF
  - `dataCapture` 会查询 TF 保存外参
  - `usb_camera.py` 会发布鱼眼相机简易 TF
  - `dataPublish` 会在回放时重新广播 TF

### 与硬件或外部程序的通信

- 串口
  - `serial_gripper_imu.cpp`
  - 波特率 `460800`
  - 用 boost::asio 直接读写二进制命令
- USB / V4L2
  - `usb_camera.py`
  - 通过 `/dev/video*` 访问鱼眼相机
- RealSense SDK / ROS 驱动
  - `realsense2_camera/launch/rs_launch.py`
- Diana SDK / 网络
  - `teleop_diana.py`
  - 通过 `robot_ip` 连接 Diana 机械臂
- 外部定位系统
  - 代码中通过 `pika_locator` launch 使用
  - 本仓库不包含该包实现

### 外部手册可补充的接口含义

- 已确认：手册说明左右手需要分别绑定：
  - 串口设备
  - 鱼眼相机口
  - RealSense 序列号
  - 定位标签代码
- 已确认：手册说明双手配置错误会导致左右数据录制错位。
- 已确认：手册提到夹爪控制接口以 `/gripper/ctrl`、`/joint_states*` 等形式暴露，这与本仓库 topic 设计一致。
- 需结合设备文档确认：
  - 串口协议字段定义
  - IMU 姿态输出坐标系
  - 定位标签与 `pika_pose` 坐标原点关系

## 9. 坐标系与消息格式

### 已在代码中出现的坐标相关对象

- `PoseStamped`
  - `pika_pose`
  - `arm_end_pose`
  - localization pose
- `JointState`
  - 机械臂关节
  - 夹爪开合量
- `Gripper`
  - 夹爪角度、距离、电流、速度、温度、状态
- `Imu`
  - 姿态四元数、角速度、线加速度
- `Odometry`
  - 底盘速度/里程
- TF
  - 相机 parent frame
  - 传感器 child frame

### 代码里能确认的约定

- 已确认：`teleop_diana` 以 `base_link` 作为发布 `arm_end_pose` 的 `frame_id`。
- 已确认：`teleop_diana` 内部把 `pika_pose` 四元数转成 RPY，再经 `pika_to_arm` 修正。
- 已确认：`usb_camera.py` 生成的图像 `frame_id` 是 `camera_frame_id + "_color"`。
- 已确认：`data_tools` 配置文件中显式维护各模态 `parentFrames`。
- 已确认：`single_pika_teleop_data_params.yaml` 里出现：
  - `gripper/camera_link`
  - `gripper/camera_fisheye_link`
  - `global_camera_color_optical_frame`

### 单位、维度、顺序

- 已确认：
  - `pika_to_arm` 为 6 维 `[x, y, z, roll, pitch, yaw]`
  - `teleop_diana` 中姿态换算使用 RPY 与 rotvec
  - Diana TCP pose 为 6 维 `[x, y, z, rx, ry, rz]`
- 推测：
  - `teleop_diana` 中位置单位应为米，姿态单位应为弧度
  - `Gripper.angle` 单位应为弧度，`Gripper.distance` 单位应为米
- 需特别小心：
  - `distance` 到 `angle` 之间存在非线性几何映射，不是线性比例
  - 同一夹爪信息同时以 `Gripper` 和 `JointState` 表示，语义不完全一样
  - `pika_to_arm` 坐标修正若方向错，会直接导致遥操作方向错位
  - `global_camera_color_optical_frame` 与 `camera_link` 风格不同，说明不同相机可能使用不同 frame 约定

## 10. 风险点与不确定点

### 已确认的风险点

- `teleop_diana.py`
  - `pika_to_arm` 填错会导致位姿映射错误。
  - 遥操作开始/结束依赖 `takeover` / `flag` 状态切换，状态不同步会直接影响是否持续下发控制。
- `serial_gripper_imu.cpp`
  - 夹爪控制和状态反馈复用同一串口节点，控制、读回、灯振提示耦合较高。
  - `jointStateCtrlHandler()` 和 `gripperCtrlHandler()` 都可能下发位置命令，来源冲突时要查谁在发。
  - 代码中电流保护判断被注释掉了，过载保护更多依赖外部状态或设备自身。
- `dataCapture.cpp`
  - 用 topic 频率作为采集健康判断，时钟异常或消息 burst 可能误判。
  - TF 保存依赖运行时 `lookupTransform()` 成功，若 TF 暂时不完整会影响标定信息落盘。
- `dataSync.cpp`
  - 同步基于最近邻时间戳，`timeDiffLimit` 设太大可能错配，设太小可能丢太多帧。
- `dataPublish.cpp`
  - 回放依赖 `sync.txt`，如果先采集后忘记同步，回放结果会不完整或直接失效。

### 需结合设备文档或实机确认

- `pika_pose` 的世界系/基站系定义。
- `pika_to_arm` 的推荐值与推导方式。
- 串口协议中 `Current`、`Speed`、`Position` 的物理单位。
- `LocalizationStatus.accurate` 的判定来源。
- `ArmControlStatus.over_limit` 的发布者和触发条件。
- 左右手命名空间在完整系统中是否始终固定为 `_l` / `_r`。

### 对常见问题的定位建议

- 动作异常
  - 先看 `teleop_diana.py` 的 `pika_to_arm`、`base_pose`、`flag`
  - 再看 `pika_pose` 的方向是否稳定
- 控制不稳定
  - 先看 Diana 网络连接与 50 Hz 控制循环
  - 再看定位是否抖动
- 数据错位
  - 先看 `timeDiffLimit`
  - 再看各 topic 实际频率是否一致
- 时序不同步
  - 先看消息 header 时间是否可信
  - 再看 MCAP 是否使用 `useTopicStamp`
- 坐标变换错误
  - 先看 `parentFrames`
  - 再看 `pika_to_arm`
  - 再看 TF 存盘是否成功
- 单位错误
  - 重点查 `Gripper.distance`、TCP pose、RPY/rotvec 转换

## 11. 快速阅读路径

1. 先看入口 launch
   - [src/sensor_tools/launch/open_single_gripper.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_single_gripper.launch.py)
   - [src/data_tools/launch/run_data_capture.launch.py](/mnt/nas/projects/robot/pika_ros/src/data_tools/launch/run_data_capture.launch.py)
   - [src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_single_diana.launch.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/launch/teleop_single_diana.launch.py)
2. 再看统一配置
   - [src/data_tools/include/dataUtility.h](/mnt/nas/projects/robot/pika_ros/src/data_tools/include/dataUtility.h)
   - [src/data_tools/config/single_pika_teleop_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/single_pika_teleop_data_params.yaml)
3. 再看核心 ROS 节点
   - [src/sensor_tools/src/serial_gripper_imu.cpp](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/src/serial_gripper_imu.cpp)
   - [src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py](/mnt/nas/projects/robot/pika_ros/src/PikaAnyArm/diana/pika_remote_diana/pika_remote_diana/teleop_diana.py)
   - [src/data_tools/src/dataCapture.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataCapture.cpp)
4. 再看关键消息与服务
   - [src/data_msgs/msg/Gripper.msg](/mnt/nas/projects/robot/pika_ros/src/data_msgs/msg/Gripper.msg)
   - [src/data_msgs/msg/CaptureStatus.msg](/mnt/nas/projects/robot/pika_ros/src/data_msgs/msg/CaptureStatus.msg)
   - [src/data_msgs/srv/CaptureService.srv](/mnt/nas/projects/robot/pika_ros/src/data_msgs/srv/CaptureService.srv)
5. 最后看离线链路
   - [src/data_tools/src/dataSync.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataSync.cpp)
   - [src/data_tools/src/dataPublish.cpp](/mnt/nas/projects/robot/pika_ros/src/data_tools/src/dataPublish.cpp)

## 12. 外部设备文档待补充项

- 机械臂控制接口定义
  - Diana 当前是 TCP/SDK 控制，但手册更多描述的是 Piper/CAN 链路，需区分产品线。
- 底盘控制约束
  - `lift_data_params.yaml` 里出现底盘 odom 和 lift 状态，但仓库中没有底盘控制节点。
- 相机/传感器型号与 topic 对应关系
  - 代码已能确认 RealSense + 鱼眼，但具体型号、安装位姿、视场角需手册确认。
- 坐标系定义
  - `pika_pose` 的参考系、基站系、左右手 locator 标签定义需要设备文档。
- 安全限制
  - 夹爪电流、速度、位置限制
  - Diana 遥操作速度/加速度/阻抗限制
- 控制频率要求
  - 采集手册给出常见相机帧率，但夹爪串口、定位、机械臂控制频率边界还需外部说明。

## 附：外部文档整合结论

- 已确认：当前环境未直接解析用户给的 Yuque 页面，但通过可访问的 Pika 用户手册镜像补充到了以下信息：
  - Pika 方案包含基站/定位标签/传感器侧设备
  - 单双手场景都需要绑定 USB 口、相机口、RealSense 序列号、左右手定位标签
  - 夹爪通信与控制通过 USB/Type-C 接入工控机
  - 鱼眼、深度、定位在启动前都需要完成设备识别与绑定
- 需注意：该手册镜像描述的是较早版本流程，包含 ROS1/noetic 表述；本仓库代码实际为 ROS2/humble，命令与包名应以当前仓库为准。
