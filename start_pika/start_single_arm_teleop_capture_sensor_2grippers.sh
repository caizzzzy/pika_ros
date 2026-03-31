#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="/mnt/nas/projects/robot/pika_ros"
INSTALL_SETUP="${PROJECT_ROOT}/install/setup.bash"
ROS_SETUP="/opt/ros/humble/setup.bash"
SENSOR_TOOLS_SCRIPTS_DIR="${PROJECT_ROOT}/install/sensor_tools/share/sensor_tools/scripts"

DATASET_DIR="${HOME}/agilex/datatest_sensor_2grippers"
DEFAULT_EPISODE_INDEX=0
DATA_CAPTURE_TYPE="single_pika_teleop"

# sensor + gripper_A: 单臂遥操作链路
SENSOR_SERIAL_PORT="/dev/ttyUSB50"
GRIPPER_A_SERIAL_PORT="/dev/ttyUSB60"
SENSOR_FISHEYE_PORT="50"
GRIPPER_A_FISHEYE_PORT="60"
GRIPPER_A_DEPTH_CAMERA_NO="230422273090"

# gripper_B: 仅作为 global_camera 数据源使用
# TODO: 必须改成现场第二个 gripper_B 的深度相机序列号
GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO="TODO_SET_GRIPPER_B_DEPTH_SERIAL"

CAMERA_FPS=30
CAMERA_WIDTH=640
CAMERA_HEIGHT=480
CAMERA_PROFILE="${CAMERA_WIDTH},${CAMERA_HEIGHT},${CAMERA_FPS}"
DEVICE_CONFIG_FILE="${PROJECT_ROOT}/start_pika/single_arm_sensor_2grippers_device_config.bash"

LOG_ROOT="${PROJECT_ROOT}/start_pika/logs"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN_LOG_DIR="${LOG_ROOT}/single_arm_sensor_2grippers_${RUN_ID}"

declare -a PROCESS_NAMES=()
declare -a PROCESS_PGIDS=()

mkdir -p "${RUN_LOG_DIR}"

if [[ -f "${DEVICE_CONFIG_FILE}" ]]; then
    # setup_device.py 会生成这个文件，用于覆盖现场实际绑定到的设备参数。
    source "${DEVICE_CONFIG_FILE}"
fi

log() {
    local ts
    ts="$(date '+%F %T')"
    echo "[${ts}] $*"
}

abort() {
    log "ERROR: $*"
    exit 1
}

require_file() {
    local path="$1"
    [[ -f "${path}" ]] || abort "Missing required file: ${path}"
}

require_dir() {
    local path="$1"
    [[ -d "${path}" ]] || abort "Missing required directory: ${path}"
}

setup_checks() {
    require_file "${INSTALL_SETUP}"
    require_file "${ROS_SETUP}"
    require_dir "${SENSOR_TOOLS_SCRIPTS_DIR}"

    [[ "${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO}" != "TODO_SET_GRIPPER_B_DEPTH_SERIAL" ]] || abort \
        "请先在脚本顶部把 GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO 改成 gripper_B 的深度相机序列号。"
}

prompt_episode_index() {
    local input
    while true; do
        read -r -p "Episode 起始编号 [默认 ${DEFAULT_EPISODE_INDEX}]: " input || exit 1
        input="${input:-${DEFAULT_EPISODE_INDEX}}"
        if [[ "${input}" =~ ^[0-9]+$ ]]; then
            EPISODE_INDEX="${input}"
            return
        fi
        log "请输入非负整数。"
    done
}

build_common_shell_prefix() {
    cat <<EOF
source "${ROS_SETUP}"
source "${INSTALL_SETUP}"
EOF
}

build_conda_prefix() {
    cat <<'EOF'
if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
elif [[ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]]; then
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
elif [[ -f "${HOME}/anaconda3/etc/profile.d/conda.sh" ]]; then
    source "${HOME}/anaconda3/etc/profile.d/conda.sh"
elif [[ -f "/opt/conda/etc/profile.d/conda.sh" ]]; then
    source "/opt/conda/etc/profile.d/conda.sh"
else
    echo "Unable to initialize conda in non-interactive shell." >&2
    exit 1
fi
EOF
}

prepare_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        abort "未找到 sudo，无法完成设备权限准备。"
    fi

    log "即将检查 sudo 权限，这一步是访问串口和视频设备所必需的。"
    if ! sudo -v; then
        abort "未获得 sudo 权限，启动流程已停止。"
    fi
}

prepare_device_permissions() {
    log "准备设备权限 ..."
    sudo chmod a+rw /dev/ttyUSB* || true
    sudo chmod a+rw /dev/video* || true
}

start_managed_process() {
    local name="$1"
    local logfile="$2"
    local command_body="$3"

    log "启动 ${name} ..."
    setsid bash -lc "${command_body}" >>"${logfile}" 2>&1 &
    local pgid=$!

    PROCESS_NAMES+=("${name}")
    PROCESS_PGIDS+=("${pgid}")

    sleep 2
    if ! kill -0 "${pgid}" 2>/dev/null; then
        log "${name} 启动失败，最近日志如下："
        tail -n 40 "${logfile}" || true
        cleanup
        exit 1
    fi

    log "${name} 已启动，日志: ${logfile}"
}

cleanup() {
    local i
    for (( i=${#PROCESS_PGIDS[@]}-1; i>=0; i-- )); do
        local pgid="${PROCESS_PGIDS[$i]}"
        local name="${PROCESS_NAMES[$i]}"
        if kill -0 "${pgid}" 2>/dev/null; then
            log "停止 ${name} (PGID ${pgid}) ..."
            kill -"TERM" -- "-${pgid}" 2>/dev/null || true
        fi
    done

    sleep 2

    for (( i=${#PROCESS_PGIDS[@]}-1; i>=0; i-- )); do
        local pgid="${PROCESS_PGIDS[$i]}"
        local name="${PROCESS_NAMES[$i]}"
        if kill -0 "${pgid}" 2>/dev/null; then
            log "${name} 仍未退出，发送 KILL ..."
            kill -"KILL" -- "-${pgid}" 2>/dev/null || true
        fi
    done
}

on_exit() {
    local code=$?
    cleanup
    if [[ ${code} -eq 0 ]]; then
        log "启动器已退出。"
    else
        log "启动器异常退出，退出码: ${code}"
    fi
}

show_summary() {
    cat <<EOF

============================================================
单臂遥操作 + 数据采集（1 sensor + 2 grippers）已启动
日志目录: ${RUN_LOG_DIR}
datasetDir: ${DATASET_DIR}
episodeIndex: ${EPISODE_INDEX}

角色分配:
  - sensor + gripper_A: 单臂遥操作链路
  - gripper_B: 仅作为 global_camera 数据源
  - 原默认 external global realsense: 不使用

已启动进程:
  1. sensor_gripper_with_gripperB_global_camera
  2. teleop_single_diana
  3. data_capture

退出方式:
  - 保持这个脚本前台运行
  - 需要整体关闭时，在本脚本终端按 Ctrl+C
============================================================

EOF
}

main() {
    trap on_exit EXIT
    trap 'exit 130' INT TERM

    setup_checks
    prompt_episode_index

    log "本次运行日志目录: ${RUN_LOG_DIR}"
    log "datasetDir 固定为: ${DATASET_DIR}"
    log "episodeIndex 起始为: ${EPISODE_INDEX}"
    log "gripper_B global camera serial: ${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO}"

    prepare_sudo
    prepare_device_permissions

    local common_prefix
    local conda_prefix
    common_prefix="$(build_common_shell_prefix)"
    conda_prefix="$(build_conda_prefix)"

    start_managed_process \
        "sensor_gripper_with_gripperB_global_camera" \
        "${RUN_LOG_DIR}/sensor_gripper_with_gripperB_global_camera.log" \
        "${common_prefix}
cd \"${SENSOR_TOOLS_SCRIPTS_DIR}\"
chmod 777 usb_camera.py
exec ros2 launch sensor_tools open_sensor_gripper.launch.py \
    enable_global_camera:=true \
    global_camera_name:=global_camera \
    global_camera_serial_no:=${GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO} \
    sensor_serial_port:=${SENSOR_SERIAL_PORT} \
    gripper_serial_port:=${GRIPPER_A_SERIAL_PORT} \
    sensor_fisheye_port:=${SENSOR_FISHEYE_PORT} \
    gripper_fisheye_port:=${GRIPPER_A_FISHEYE_PORT} \
    gripper_depth_camera_no:=_${GRIPPER_A_DEPTH_CAMERA_NO} \
    camera_fps:=${CAMERA_FPS} \
    camera_width:=${CAMERA_WIDTH} \
    camera_height:=${CAMERA_HEIGHT} \
    camera_profile:=${CAMERA_PROFILE}"

    start_managed_process \
        "teleop_single_diana" \
        "${RUN_LOG_DIR}/teleop_single_diana.log" \
        "${common_prefix}
${conda_prefix}
conda activate pika
exec ros2 launch pika_remote_diana teleop_single_diana.launch.py"

    start_managed_process \
        "data_capture" \
        "${RUN_LOG_DIR}/data_capture.log" \
        "${common_prefix}
exec ros2 launch data_tools run_data_capture.launch.py useService:=true type:=${DATA_CAPTURE_TYPE} datasetDir:=${DATASET_DIR} episodeIndex:=${EPISODE_INDEX}"

    show_summary

    while true; do
        sleep 5
        local i
        for (( i=0; i<${#PROCESS_PGIDS[@]}; i++ )); do
            if ! kill -0 "${PROCESS_PGIDS[$i]}" 2>/dev/null; then
                log "${PROCESS_NAMES[$i]} 已退出，请查看日志: ${RUN_LOG_DIR}"
                exit 1
            fi
        done
    done
}

main "$@"
