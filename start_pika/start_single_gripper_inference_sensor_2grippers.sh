#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="/mnt/nas/projects/robot/pika_ros"
ROS_SETUP="/opt/ros/humble/setup.bash"
INSTALL_SETUP="${PROJECT_ROOT}/install/setup.bash"
SENSOR_TOOLS_SCRIPTS_DIR="${PROJECT_ROOT}/install/sensor_tools/share/sensor_tools/scripts"
DEVICE_CONFIG_FILE="${PROJECT_ROOT}/start_pika/single_arm_sensor_2grippers_device_config.bash"

# 默认值会在存在设备配置文件时被覆盖
GRIPPER_A_SERIAL_PORT="/dev/ttyUSB60"
GRIPPER_A_FISHEYE_PORT="60"
GRIPPER_A_DEPTH_CAMERA_NO="230422273090"
GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO="TODO_SET_GRIPPER_B_DEPTH_SERIAL"

CAMERA_FPS=30
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_PROFILE="${CAMERA_WIDTH},${CAMERA_HEIGHT},${CAMERA_FPS}"
JOINT_NAME="center_joint"

if [[ -f "${DEVICE_CONFIG_FILE}" ]]; then
    # setup_device.py 的第 4 种模式会生成这个文件。
    source "${DEVICE_CONFIG_FILE}"
fi

abort() {
    echo "[ERROR] $*" >&2
    exit 1
}

require_file() {
    local path="$1"
    [[ -f "${path}" ]] || abort "Missing required file: ${path}"
}

prepare_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        abort "未找到 sudo，无法完成设备权限准备。"
    fi

    if ! sudo -v; then
        abort "未获得 sudo 权限，启动流程已停止。"
    fi
}

main() {
    require_file "${ROS_SETUP}"
    require_file "${INSTALL_SETUP}"

    [[ "${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO}" != "TODO_SET_GRIPPER_B_DEPTH_SERIAL" ]] || abort \
        "请先运行 scripts/setup_device.py 的第 4 种模式，或手动设置 GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO。"

    prepare_sudo

    sudo chmod a+rw /dev/ttyUSB* || true
    sudo chmod a+rw /dev/video* || true

    source "${ROS_SETUP}"
    cd "${SENSOR_TOOLS_SCRIPTS_DIR}"
    chmod 777 usb_camera.py

    source "${INSTALL_SETUP}"
    exec ros2 launch sensor_tools open_single_gripper.launch.py \
        serial_port:="${GRIPPER_A_SERIAL_PORT}" \
        fisheye_port:="${GRIPPER_A_FISHEYE_PORT}" \
        camera_serial_no:="${GRIPPER_A_DEPTH_CAMERA_NO}" \
        enable_global_camera:=true \
        global_camera_name:=global_camera \
        global_camera_serial_no:="${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO}" \
        camera_fps:="${CAMERA_FPS}" \
        camera_width:="${CAMERA_WIDTH}" \
        camera_height:="${CAMERA_HEIGHT}" \
        camera_profile:="${CAMERA_PROFILE}" \
        joint_name:="${JOINT_NAME}" \
        "$@"
}

main "$@"
