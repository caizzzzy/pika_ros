#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT="${SCRIPT_DIR}/.."
DEVICE_CONFIG_FILE="${PROJECT_ROOT}/start_pika/single_arm_sensor_2grippers_device_config.bash"

camera_fps=30
camera_width=640
camera_height=480

# 默认值会在存在设备配置文件时被覆盖
gripper_serial_port=/dev/ttyUSB60
gripper_fisheye_port=60
gripper_depth_camera_no=230422273090
global_camera_serial_no=TODO_SET_GRIPPER_B_DEPTH_SERIAL
joint_name=center_joint

if [[ -f "${DEVICE_CONFIG_FILE}" ]]; then
    # setup_device.py 的第 4 种模式会生成这个文件
    source "${DEVICE_CONFIG_FILE}"
    gripper_serial_port="${GRIPPER_A_SERIAL_PORT:-$gripper_serial_port}"
    gripper_fisheye_port="${GRIPPER_A_FISHEYE_PORT:-$gripper_fisheye_port}"
    gripper_depth_camera_no="${GRIPPER_A_DEPTH_CAMERA_NO:-$gripper_depth_camera_no}"
    global_camera_serial_no="${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO:-$global_camera_serial_no}"
fi

if [[ "${global_camera_serial_no}" == "TODO_SET_GRIPPER_B_DEPTH_SERIAL" ]]; then
    echo "[ERROR] 请先运行 scripts/setup_device.py 的第 4 种模式，或手动设置 global_camera_serial_no。" >&2
    exit 1
fi

sudo chmod a+rw /dev/ttyUSB* || true
sudo chmod a+rw /dev/video* || true

# ROS setup scripts are not always nounset-safe, so source them with `set +u`.
set +u
source /opt/ros/humble/setup.bash
cd "${SCRIPT_DIR}/../install/sensor_tools/share/sensor_tools/scripts/"
chmod 777 usb_camera.py || true

source "${SCRIPT_DIR}/../install/setup.bash"
set -u
exec ros2 launch sensor_tools open_single_gripper.launch.py \
    serial_port:="${gripper_serial_port}" \
    fisheye_port:="${gripper_fisheye_port}" \
    camera_serial_no:="${gripper_depth_camera_no}" \
    enable_global_camera:=true \
    global_camera_name:=global_camera \
    global_camera_serial_no:="${global_camera_serial_no}" \
    camera_fps:="${camera_fps}" \
    camera_width:="${camera_width}" \
    camera_height:="${camera_height}" \
    camera_profile:="${camera_width},${camera_height},${camera_fps}" \
    joint_name:="${joint_name}" \
    "$@"
