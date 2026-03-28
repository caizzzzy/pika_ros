#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="/mnt/nas/projects/robot/pika_ros"
INSTALL_SETUP="${PROJECT_ROOT}/install/setup.bash"
SURVIVE_DIR="${PROJECT_ROOT}/install/libsurvive/bin"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
SENSOR_SCRIPT="${SCRIPTS_DIR}/start_multi_sensor.bash"
GRIPPER_SCRIPT="${SCRIPTS_DIR}/start_multi_gripper.bash"

DATASET_DIR="${HOME}/agilex/data_multi_pika_teleop"
DEFAULT_EPISODE_INDEX=0
DATA_CAPTURE_TYPE="multi_pika_teleop"

LOG_ROOT="${PROJECT_ROOT}/start_pika/logs"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN_LOG_DIR="${LOG_ROOT}/dual_arm_${RUN_ID}"

declare -a PROCESS_NAMES=()
declare -a PROCESS_PGIDS=()

mkdir -p "${RUN_LOG_DIR}"

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
    require_dir "${SURVIVE_DIR}"
    require_file "${SENSOR_SCRIPT}"
    require_file "${GRIPPER_SCRIPT}"
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

confirm_continue() {
    local prompt="$1"
    local answer
    while true; do
        read -r -p "${prompt} [y/n]: " answer || exit 1
        case "${answer}" in
            y|Y) return 0 ;;
            n|N) return 1 ;;
            *) log "请输入 y 或 n。" ;;
        esac
    done
}

run_survive_cli() {
    log "步骤 1/5: 前台启动 survive-cli。"
    log "请你根据现场情况观察基站校准结果；确认完成后由你本人按 Ctrl+C 结束。"
    log "如果这一步失败，可以重复执行；主脚本不会自动跳过你的判断。"
    echo

    while true; do
        (
            cd "${SURVIVE_DIR}"
            exec ./survive-cli
        )

        echo
        if confirm_continue "survive-cli 已结束，是否确认基站状态已经满足继续启动"; then
            break
        fi

        if ! confirm_continue "是否重新运行 survive-cli"; then
            abort "用户取消启动流程。"
        fi

        echo
    done
}

build_common_shell_prefix() {
    cat <<EOF
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

build_optional_conda_reset_prefix() {
    cat <<'EOF'
if command -v conda >/dev/null 2>&1; then
    eval "$(conda shell.bash hook)"
    conda deactivate >/dev/null 2>&1 || true
elif [[ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]]; then
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
    conda deactivate >/dev/null 2>&1 || true
elif [[ -f "${HOME}/anaconda3/etc/profile.d/conda.sh" ]]; then
    source "${HOME}/anaconda3/etc/profile.d/conda.sh"
    conda deactivate >/dev/null 2>&1 || true
elif [[ -f "/opt/conda/etc/profile.d/conda.sh" ]]; then
    source "/opt/conda/etc/profile.d/conda.sh"
    conda deactivate >/dev/null 2>&1 || true
fi
EOF
}

prepare_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        abort "未找到 sudo，无法执行双传感器/双夹爪脚本中的设备权限配置。"
    fi

    log "即将检查 sudo 权限，这一步是启动双臂链路所必需的。"
    if ! sudo -v; then
        abort "未获得 sudo 权限，启动流程已停止。"
    fi
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
双臂遥操作 + 数据采集 已启动
日志目录: ${RUN_LOG_DIR}
datasetDir: ${DATASET_DIR}
episodeIndex: ${EPISODE_INDEX}

已启动进程:
  1. multi sensor
  2. multi gripper
  3. teleop_double_diana
  4. data capture

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

    run_survive_cli

    local common_prefix
    local conda_prefix
    local optional_conda_reset_prefix
    common_prefix="$(build_common_shell_prefix)"
    conda_prefix="$(build_conda_prefix)"
    optional_conda_reset_prefix="$(build_optional_conda_reset_prefix)"

    prepare_sudo

    start_managed_process \
        "multi_sensor" \
        "${RUN_LOG_DIR}/multi_sensor.log" \
        "${common_prefix}
${optional_conda_reset_prefix}
cd \"${SCRIPTS_DIR}\"
export PATH=/usr/bin:\$PATH
exec bash \"${SENSOR_SCRIPT}\" sensor"

    start_managed_process \
        "multi_gripper" \
        "${RUN_LOG_DIR}/multi_gripper.log" \
        "${common_prefix}
${optional_conda_reset_prefix}
cd \"${SCRIPTS_DIR}\"
export PATH=/usr/bin:\$PATH
exec bash \"${GRIPPER_SCRIPT}\" gripper sensor"

    start_managed_process \
        "teleop_double_diana" \
        "${RUN_LOG_DIR}/teleop_double_diana.log" \
        "${common_prefix}
${conda_prefix}
conda activate pika
exec ros2 launch pika_remote_diana teleop_double_diana.launch.py"

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
