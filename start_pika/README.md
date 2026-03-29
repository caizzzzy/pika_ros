# Start Pika

**DATASET_DIR**
记得要改

`start_pika/` 目录下放的是面向实验使用的独立启动器。每个脚本只负责一种场景，不做总控合并。

## 启动脚本列表

0. 采集后自动处理：同步 + HDF5 转换

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/process_pika_dataset.sh
```

这个脚本会交互式让你选择:

- 单夹持器
- 双夹持器
- 单夹持器遥操作
- 双夹持器遥操作

随后自动执行:

- `ros2 launch data_tools run_data_sync.launch.py ...`
- `python3 scripts/data_to_hdf5.py ...`

并支持你输入:

- `datasetDir`
- `episodeIndex`
  - `-1` 表示处理全部 episode
  - 非负整数表示只处理对应的 `episode{N}`

脚本顶部的 `DEFAULT_DATASET_DIR` 是四种 type 共用的默认目录；如果你每次采集后都会自己改目录名，改这一处就够了。

1. 单臂遥操作 + 数据采集

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture.sh
```

对应链路:

- `survive-cli`
- `scripts/start_sensor_gripper.bash`
- `ros2 launch pika_remote_diana teleop_single_diana.launch.py`
- `ros2 launch data_tools run_data_capture.launch.py type:=single_pika_teleop`

2. 单传感器采集

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/start_single_sensor_capture.sh
```

对应链路:

- `survive-cli`
- `scripts/start_single_sensor.bash`
- `ros2 launch data_tools run_data_capture.launch.py type:=single_pika`

3. 双传感器采集

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/start_multi_sensor_capture.sh
```

对应链路:

- `survive-cli`
- `scripts/start_multi_sensor.bash`
- `ros2 launch data_tools run_data_capture.launch.py type:=multi_pika`

4. 双臂遥操作 + 数据采集

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/start_dual_arm_teleop_capture.sh
```

对应链路:

- `survive-cli`
- `scripts/start_multi_sensor.bash sensor`
- `scripts/start_multi_gripper.bash gripper sensor`
- `ros2 launch pika_remote_diana teleop_double_diana.launch.py`
- `ros2 launch data_tools run_data_capture.launch.py type:=multi_pika_teleop`

5. 单臂遥操作 + 数据采集（1 sensor + 2 grippers，第二个 gripper 充当 global_camera）

```bash
bash /mnt/nas/projects/robot/pika_ros/start_pika/start_single_arm_teleop_capture_sensor_2grippers.sh
```

对应链路:

- `survive-cli`
- `ros2 launch sensor_tools open_sensor_gripper.launch.py ...`
- `ros2 launch pika_remote_diana teleop_single_diana.launch.py`
- `ros2 launch data_tools run_data_capture.launch.py type:=single_pika_teleop`

这个场景的特殊点:

- `sensor + gripper_A` 负责单臂遥操作
- `gripper_B` 不参与机械臂控制，只提供 `global_camera` 的深度相机数据
- 需要你手动在脚本顶部填写 `GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO`
- 这条链路复用了现有 `/global_camera/...` 数据采集配置，因此不需要额外改 `data_tools` YAML

## 通用使用方式

1. 运行脚本后，先输入本次采集要使用的 `episodeIndex` 起始编号。
2. 脚本会前台启动 `survive-cli`。
3. 基站状态由你自己观察和判断，确认完成后由你本人按 `Ctrl+C` 结束 `survive-cli`。
4. 退出 `survive-cli` 后，脚本会再次询问是否继续；确认后才会启动后续长期运行进程。
5. 主脚本保持前台运行；需要整体关闭时，在主脚本终端按 `Ctrl+C`，脚本会清理它拉起的后台进程。

## 日志

日志目录位于:

```text
/mnt/nas/projects/robot/pika_ros/start_pika/logs/
```

每次运行会创建独立子目录，例如:

```text
single_sensor_20260328_153000
multi_sensor_20260328_153500
dual_arm_20260328_154200
20260328_152000
```

每个长期运行进程都会写自己的日志文件，方便单独排查。

## datasetDir

每个脚本都把 `datasetDir` 固定写在脚本内部，按你之前的要求，不在命令行里传。

默认值分别是:

- `start_single_arm_teleop_capture.sh`: `$HOME/agilex/datatest`
- `start_single_sensor_capture.sh`: `$HOME/agilex/data_single_pika`
- `start_multi_sensor_capture.sh`: `$HOME/agilex/data_multi_pika`
- `start_dual_arm_teleop_capture.sh`: `$HOME/agilex/data_multi_pika_teleop`
- `start_single_arm_teleop_capture_sensor_2grippers.sh`: `$HOME/agilex/datatest_sensor_2grippers`

如需修改数据保存目录，请直接编辑对应脚本里的 `DATASET_DIR`。

## 说明

- 这些启动器不会修改现有业务脚本，只是调用现有链路。
- `survive-cli` 没有被静默后台化，而是保留为前台交互步骤。这是故意的，因为它依赖人工判断是否成功、也可能需要重复尝试。
- 某些底层启动脚本会访问设备权限或调用 `sudo`；启动器会在进入后台流程前先做权限检查，避免后台卡在密码提示上。
