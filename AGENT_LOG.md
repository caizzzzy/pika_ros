**文件清单**
我这轮已经改过/新增过的文件路径如下：

- [docs/PROJECT_OVERVIEW.md](/mnt/nas/projects/robot/pika_ros/docs/PROJECT_OVERVIEW.md)
- [src/sensor_tools/launch/open_single_sensor.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_single_sensor.launch.py)
- [src/sensor_tools/launch/open_sensor_gripper.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_sensor_gripper.launch.py)
- [src/sensor_tools/launch/open_multi_sensor.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_multi_sensor.launch.py)
- [src/sensor_tools/launch/open_multi_gripper.launch.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/launch/open_multi_gripper.launch.py)
- [src/data_tools/config/single_pika_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/single_pika_data_params.yaml)
- [src/data_tools/config/multi_pika_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/multi_pika_data_params.yaml)
- [src/data_tools/config/multi_pika_teleop_data_params.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/multi_pika_teleop_data_params.yaml)
- [src/data_tools/config/single_pika_teleop_data_params_prior.yaml](/mnt/nas/projects/robot/pika_ros/src/data_tools/config/single_pika_teleop_data_params_prior.yaml)
- [start_pika/start_single_arm_teleop_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture.sh)
- [start_pika/start_single_sensor_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_sensor_capture.sh)
- [start_pika/start_multi_sensor_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_multi_sensor_capture.sh)
- [start_pika/start_dual_arm_teleop_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_dual_arm_teleop_capture.sh)
- [start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh)
- [start_pika/README.md](/mnt/nas/projects/robot/pika_ros/start_pika/README.md)
- [scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/scripts/setup_device.py)
- [src/sensor_tools/scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/setup_device.py)

**每个文件做了什么**
- [docs/PROJECT_OVERVIEW.md](/mnt/nas/projects/robot/pika_ros/docs/PROJECT_OVERVIEW.md)
  - 修改前：项目总览文档。
  - 修改后：补充了 `setup_device.py` 的用途、绑定模式表，以及“1 sensor + 2 grippers，其中 gripper_B 作为 global_camera”的关键 topic 清单。
  - 原因：让后续使用和排查有文档依据。

- 四个 `sensor_tools/launch/*.launch.py`
  - 修改前：部分场景没有内置 `global_camera`，或只在单夹爪里有。
  - 修改后：都支持 `enable_global_camera/global_camera_name/global_camera_serial_no`，可在 launch 内直接拉起 `/global_camera/*`。
  - 原因：统一“global_camera 随启动链启动”的能力。

- 四个 `data_tools/config/*.yaml`
  - 修改前：只有单臂 teleop 明确采集 `/global_camera/*`。
  - 修改后：单/双采集、双臂 teleop 等配置都加入了 `/global_camera/*`。
  - 原因：让 episode 采集链可以记录 global camera。

- [start_pika/start_single_arm_teleop_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture.sh)
  - 修改前：不存在。
  - 修改后：单臂遥操作 + 数据采集一键启动器。
  - 原因：替代多终端手工启动。

- [start_pika/start_single_sensor_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_sensor_capture.sh)
  - 修改前：不存在。
  - 修改后：单传感器采集一键启动器。
  - 原因：补齐常用场景入口。

- [start_pika/start_multi_sensor_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_multi_sensor_capture.sh)
  - 修改前：不存在。
  - 修改后：双传感器采集一键启动器。
  - 原因：补齐常用场景入口。

- [start_pika/start_dual_arm_teleop_capture.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_dual_arm_teleop_capture.sh)
  - 修改前：不存在。
  - 修改后：双臂遥操作 + 数据采集一键启动器。
  - 原因：补齐常用场景入口。

- [start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh](/mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh)
  - 修改前：不存在。
  - 修改后：专门适配“1 sensor + 2 grippers，gripper_B 充当 global_camera”的启动器；会读取设备配置文件覆盖现场参数。
  - 原因：这是你当前最关心的特殊硬件组合。

- [start_pika/README.md](/mnt/nas/projects/robot/pika_ros/start_pika/README.md)
  - 修改前：原先不存在，后面是简单说明。
  - 修改后：整理成 `start_pika/` 所有启动器的总说明。
  - 原因：集中说明入口和使用方式。

- [scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/scripts/setup_device.py) 和 [src/sensor_tools/scripts/setup_device.py](/mnt/nas/projects/robot/pika_ros/src/sensor_tools/scripts/setup_device.py)
  - 修改前：支持 3 种设备绑定模式，生成 `setup_*.bash` 和 `start_*.bash`。
  - 修改后：新增第 4 种模式“1 sensor + 2 grippers，第二个 gripper 作为 global_camera”，并额外生成 `start_pika/single_arm_sensor_2grippers_device_config.bash`。
  - 原因：让特殊硬件组合也能走同样的“识别设备 -> 生成绑定 -> 启动”流程。

**当前完整调用链**
当前你这套特殊场景的完整入口是：

1. 先运行设备绑定工具：
   - `python3 /mnt/nas/projects/robot/pika_ros/scripts/setup_device.py`
   - 选择模式 `4`

2. `setup_device.py` 会：
   - 识别 `sensor`
   - 识别 `gripper_A（teleop）`
   - 识别 `gripper_B（global_camera）`
   - 生成：
     - `setup_sensor_2grippers_global_camera.bash`
     - `start_sensor_2grippers_global_camera.bash`
     - [single_arm_sensor_2grippers_device_config.bash](/mnt/nas/projects/robot/pika_ros/start_pika/single_arm_sensor_2grippers_device_config.bash)
   - 执行 `setup_sensor_2grippers_global_camera.bash`

3. 之后你运行真正的启动入口：
   - `bash /mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh`

4. 这个入口脚本会读取：
   - [install/setup.bash](/mnt/nas/projects/robot/pika_ros/install/setup.bash)
   - 如果存在的话，读取 [single_arm_sensor_2grippers_device_config.bash](/mnt/nas/projects/robot/pika_ros/start_pika/single_arm_sensor_2grippers_device_config.bash)
   - 用户输入的 `episodeIndex`

5. 它会启动：
   - 前台：`install/libsurvive/bin/survive-cli`
   - 后台：`ros2 launch sensor_tools open_sensor_gripper.launch.py ...`
   - 后台：`ros2 launch pika_remote_diana teleop_single_diana.launch.py`
   - 后台：`ros2 launch data_tools run_data_capture.launch.py useService:=true type:=single_pika_teleop ...`

**角色定义**
- `sensor`
  - 提供 teleop 的 sensor 侧输入链路。
  - 仍使用 `/sensor/gripper/*`、`/pika_pose` 等原有结构。

- `gripper_A`
  - 是真正参与单臂遥操作控制的 gripper。
  - 提供 `/gripper/gripper/*`、`/gripper/camera/*`、`/gripper/camera_fisheye/*` 这一路。

- `gripper_B`
  - 不参与机械臂控制。
  - 不单独起 gripper 串口控制节点。
  - 它的深度相机序列号被塞给 `global_camera_serial_no`，于是它以 `/global_camera/*` 的身份出现。

- 原本 realsense global_camera 的角色
  - 现在由 `gripper_B` 的深度相机替代。

**你后续怎么用**
- 第一次上这套特殊硬件：
  1. 跑 `python3 scripts/setup_device.py`
  2. 选 `4`
  3. 按提示依次插 `sensor`、`gripper_A`、`gripper_B`
  4. 等它生成绑定文件并执行 udev 绑定

- 之后日常启动：
  1. 跑 `bash start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh`
  2. 输入 `episodeIndex`
  3. 前台完成 `survive-cli`
  4. 确认后让它自动拉起 teleop 和 data capture

**尚未验证的假设**
- `gripper_B` 只作为 `global_camera` 使用时，不需要额外执行你提到的文档 2.6/2.7 的完整第二 gripper 控制配置。
- `open_sensor_gripper.launch.py` 里把 `global_camera_serial_no` 换成 gripper_B 的深度相机序列号后，topic 行为会和原外部 RealSense 一致。
- `single_pika_teleop_data_params.yaml` 现有 `/global_camera/*` 订阅配置足以直接复用，不需要再改 topic 名。
- 现场的 `conda activate pika`、`sudo`、设备权限、USB 口绑定方式与当前脚本假设一致。

**最可能出错的地方**
- `setup_device.py` 识别设备时：
  - `rs-enumerate-devices -s` 只能稳定识别当前单插设备
  - 鱼眼摄像头的人工选取可能误选

- 现场 USB 口变化：
  - 这个方案高度依赖“配置完成后仍插回同一个 USB 口”

- `gripper_B` 只想当 global camera，但当前第 4 模式仍绑定了它的串口和鱼眼：
  - 如果你现场其实没接这两路，绑定检查可能偏严格

- `global_camera` 的真实来源替换：
  - 虽然代码上已经替换为 `gripper_B` 的深度相机，但没做实机验证前，不能 100% 保证 frame、topic、数据率都完全符合预期

- `start_single_arm_teleop_capture_sensor_2grippers.sh`
  - 需要依赖 `start_pika/single_arm_sensor_2grippers_device_config.bash`
  - 这个文件不是仓库预置文件，必须先跑 `setup_device.py` 第 4 模式才会生成

如果你下一步想要的只是“使用前检查清单”，我可以在不改代码的前提下，继续给你整理一份最短的现场操作顺序和 topic 核对清单。