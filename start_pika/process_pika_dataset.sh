#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="/mnt/nas/projects/robot/pika_ros"
INSTALL_SETUP_SH="${PROJECT_ROOT}/install/setup.sh"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
HDF5_SCRIPT="${SCRIPTS_DIR}/data_to_hdf5.py"

# 默认数据目录。四种 type 都共用这里，方便你按实验批次自行改名。
DEFAULT_DATASET_DIR="${HOME}/agilex/data"

LOG_ROOT="${PROJECT_ROOT}/start_pika/logs"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN_LOG_DIR="${LOG_ROOT}/process_data_${RUN_ID}"

DATA_TYPE=""
DATA_LABEL=""
DATASET_DIR=""
EPISODE_INDEX=""
EPISODE_NAME=""
SYNC_IMPL="configurable"
SYNC_IMPL_LABEL="可配置混合同步"
CAMERA_COLOR_POLICY="nearest"
CAMERA_DEPTH_POLICY="nearest"
CAMERA_POINT_CLOUD_POLICY="nearest"
ARM_JOINT_STATE_POLICY="causal"
ARM_END_POSE_POLICY="causal"
LOCALIZATION_POSE_POLICY="causal"
GRIPPER_ENCODER_POLICY="causal"
IMU_9AXIS_POLICY="causal"
LIDAR_POINT_CLOUD_POLICY="causal"
ROBOT_BASE_VEL_POLICY="causal"
LIFT_MOTOR_POLICY="causal"

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
    require_file "${INSTALL_SETUP_SH}"
    require_dir "${SCRIPTS_DIR}"
    require_file "${HDF5_SCRIPT}"
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

choose_data_type() {
    local input
    while true; do
        cat <<'EOF'

请选择数据类型:
  1. 单夹持器           (single_pika)
  2. 双夹持器           (multi_pika)
  3. 单夹持器遥操作     (single_pika_teleop)
  4. 双夹持器遥操作     (multi_pika_teleop)
EOF
        read -r -p "输入编号 [1-4]: " input || exit 1
        case "${input}" in
            1)
                DATA_TYPE="single_pika"
                DATA_LABEL="单夹持器"
                DATASET_DIR="${DEFAULT_DATASET_DIR}"
                return
                ;;
            2)
                DATA_TYPE="multi_pika"
                DATA_LABEL="双夹持器"
                DATASET_DIR="${DEFAULT_DATASET_DIR}"
                return
                ;;
            3)
                DATA_TYPE="single_pika_teleop"
                DATA_LABEL="单夹持器遥操作"
                DATASET_DIR="${DEFAULT_DATASET_DIR}"
                return
                ;;
            4)
                DATA_TYPE="multi_pika_teleop"
                DATA_LABEL="双夹持器遥操作"
                DATASET_DIR="${DEFAULT_DATASET_DIR}"
                return
                ;;
            *)
                log "请输入 1 到 4 之间的编号。"
                ;;
        esac
    done
}

prompt_dataset_dir() {
    local input
    while true; do
        read -r -p "datasetDir [默认 ${DATASET_DIR}]: " input || exit 1
        input="${input:-${DATASET_DIR}}"

        if [[ -d "${input}" ]]; then
            DATASET_DIR="${input}"
            return
        fi

        if confirm_continue "目录不存在，是否自动创建 ${input}"; then
            mkdir -p "${input}"
            DATASET_DIR="${input}"
            return
        fi
    done
}

prompt_episode_index() {
    local input
    while true; do
        read -r -p "episodeIndex [默认 -1，-1 表示处理全部 episode]: " input || exit 1
        input="${input:--1}"
        if [[ "${input}" =~ ^-1$|^[0-9]+$ ]]; then
            EPISODE_INDEX="${input}"
            if [[ "${EPISODE_INDEX}" == "-1" ]]; then
                EPISODE_NAME=""
            else
                EPISODE_NAME="episode${EPISODE_INDEX}"
            fi
            return
        fi
        log "请输入 -1 或非负整数。"
    done
}

prompt_sync_strategy() {
    local input
    while true; do
        cat <<'EOF'

请选择同步策略:
  1. 推荐混合模式   图像 nearest，state/action causal
  2. 全部 nearest    与原始同步逻辑更接近
  3. 自定义          逐模态选择 nearest 或 causal
EOF
        read -r -p "输入编号 [1-3，默认 1]: " input || exit 1
        input="${input:-1}"
        case "${input}" in
            1)
                SYNC_IMPL="configurable"
                SYNC_IMPL_LABEL="推荐混合模式"
                CAMERA_COLOR_POLICY="nearest"
                CAMERA_DEPTH_POLICY="nearest"
                CAMERA_POINT_CLOUD_POLICY="nearest"
                ARM_JOINT_STATE_POLICY="causal"
                ARM_END_POSE_POLICY="causal"
                LOCALIZATION_POSE_POLICY="causal"
                GRIPPER_ENCODER_POLICY="causal"
                IMU_9AXIS_POLICY="causal"
                LIDAR_POINT_CLOUD_POLICY="causal"
                ROBOT_BASE_VEL_POLICY="causal"
                LIFT_MOTOR_POLICY="causal"
                return
                ;;
            2)
                SYNC_IMPL="configurable"
                SYNC_IMPL_LABEL="全部 nearest"
                CAMERA_COLOR_POLICY="nearest"
                CAMERA_DEPTH_POLICY="nearest"
                CAMERA_POINT_CLOUD_POLICY="nearest"
                ARM_JOINT_STATE_POLICY="nearest"
                ARM_END_POSE_POLICY="nearest"
                LOCALIZATION_POSE_POLICY="nearest"
                GRIPPER_ENCODER_POLICY="nearest"
                IMU_9AXIS_POLICY="nearest"
                LIDAR_POINT_CLOUD_POLICY="nearest"
                ROBOT_BASE_VEL_POLICY="nearest"
                LIFT_MOTOR_POLICY="nearest"
                return
                ;;
            3)
                SYNC_IMPL="configurable"
                SYNC_IMPL_LABEL="自定义混合同步"
                prompt_policy_choice "camera.color" CAMERA_COLOR_POLICY "nearest"
                prompt_policy_choice "camera.depth" CAMERA_DEPTH_POLICY "nearest"
                prompt_policy_choice "camera.pointCloud" CAMERA_POINT_CLOUD_POLICY "nearest"
                prompt_policy_choice "arm.jointState" ARM_JOINT_STATE_POLICY "causal"
                prompt_policy_choice "arm.endPose" ARM_END_POSE_POLICY "causal"
                prompt_policy_choice "localization.pose" LOCALIZATION_POSE_POLICY "causal"
                prompt_policy_choice "gripper.encoder" GRIPPER_ENCODER_POLICY "causal"
                prompt_policy_choice "imu.9axis" IMU_9AXIS_POLICY "causal"
                prompt_policy_choice "lidar.pointCloud" LIDAR_POINT_CLOUD_POLICY "causal"
                prompt_policy_choice "robotBase.vel" ROBOT_BASE_VEL_POLICY "causal"
                prompt_policy_choice "lift.motor" LIFT_MOTOR_POLICY "causal"
                return
                ;;
            *)
                log "请输入 1 到 3 之间的编号。"
                ;;
        esac
    done
}

prompt_policy_choice() {
    local label="$1"
    local __result_var="$2"
    local default_value="$3"
    local input
    while true; do
        read -r -p "${label} policy [nearest/causal，默认 ${default_value}]: " input || exit 1
        input="${input:-${default_value}}"
        case "${input}" in
            nearest|causal)
                printf -v "${__result_var}" '%s' "${input}"
                return
                ;;
            *)
                log "请输入 nearest 或 causal。"
                ;;
        esac
    done
}

show_summary() {
    cat <<EOF

============================================================
数据处理即将开始
类型: ${DATA_LABEL} (${DATA_TYPE})
datasetDir: ${DATASET_DIR}
episodeIndex: ${EPISODE_INDEX}
sync策略: ${SYNC_IMPL_LABEL}
日志目录: ${RUN_LOG_DIR}

将执行:
  1. 数据同步
  2. 转换为 HDF5
============================================================
EOF
}

run_data_sync() {
    local logfile="${RUN_LOG_DIR}/01_data_sync.log"

    log "步骤 1/2: 开始数据同步。"
    bash -lc "
set -Eeuo pipefail
source \"${INSTALL_SETUP_SH}\"
ros2 launch data_tools run_data_sync_causal.launch.py type:=\"${DATA_TYPE}\" datasetDir:=\"${DATASET_DIR}\" episodeIndex:=\"${EPISODE_INDEX}\" \
timeDiffLimit:=\"0.03\" \
camera_color_policy:=\"${CAMERA_COLOR_POLICY}\" \
camera_depth_policy:=\"${CAMERA_DEPTH_POLICY}\" \
camera_point_cloud_policy:=\"${CAMERA_POINT_CLOUD_POLICY}\" \
arm_joint_state_policy:=\"${ARM_JOINT_STATE_POLICY}\" \
arm_end_pose_policy:=\"${ARM_END_POSE_POLICY}\" \
localization_pose_policy:=\"${LOCALIZATION_POSE_POLICY}\" \
gripper_encoder_policy:=\"${GRIPPER_ENCODER_POLICY}\" \
imu_9axis_policy:=\"${IMU_9AXIS_POLICY}\" \
lidar_point_cloud_policy:=\"${LIDAR_POINT_CLOUD_POLICY}\" \
robot_base_vel_policy:=\"${ROBOT_BASE_VEL_POLICY}\" \
lift_motor_policy:=\"${LIFT_MOTOR_POLICY}\"
" |& tee "${logfile}"
}

run_hdf5_convert() {
    local logfile="${RUN_LOG_DIR}/02_data_to_hdf5.log"
    local episode_arg=()

    if [[ -n "${EPISODE_NAME}" ]]; then
        episode_arg=(--episodeName "${EPISODE_NAME}")
    fi

    log "步骤 2/2: 开始转换为 HDF5。"
    (
        cd "${SCRIPTS_DIR}"
        python3 "${HDF5_SCRIPT}" \
            --type "${DATA_TYPE}" \
            --datasetDir "${DATASET_DIR}" \
            "${episode_arg[@]}" \
            --useCameraPointCloud ""
    ) |& tee "${logfile}"
}

main() {
    setup_checks
    choose_data_type
    prompt_dataset_dir
    prompt_episode_index
    prompt_sync_strategy
    show_summary

    if ! confirm_continue "是否开始执行"; then
        abort "用户取消处理流程。"
    fi

    run_data_sync
    run_hdf5_convert

    cat <<EOF

============================================================
处理完成
类型: ${DATA_LABEL} (${DATA_TYPE})
datasetDir: ${DATASET_DIR}
episodeIndex: ${EPISODE_INDEX}
日志目录: ${RUN_LOG_DIR}
============================================================
EOF
}

main "$@"
