#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="/mnt/nas/projects/robot/pika_ros"
INSTALL_SETUP="${PROJECT_ROOT}/install/setup.bash"
SURVIVE_DIR="${PROJECT_ROOT}/install/libsurvive/bin"

abort() {
    echo "[ERROR] $*" >&2
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

main() {
    require_file "${INSTALL_SETUP}"
    require_dir "${SURVIVE_DIR}"

    echo "前台启动 survive-cli。"
    echo "请根据现场情况观察基站校准结果，确认完成后由你本人按 Ctrl+C 结束。"
    echo

    source "${INSTALL_SETUP}"
    cd "${SURVIVE_DIR}"
    exec ./survive-cli
}

main "$@"
