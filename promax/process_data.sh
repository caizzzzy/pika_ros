#!/bin/bash

# ================= 配置区域 =================
# 项目根目录 (NAS路径)
PIKA_WS="/mnt/nas/projects/robot/pika_ros"
# 数据存放目录 (根据你提供的流程，默认在 ~/agilex/data)/home/robot/agilex/data_umi202
DATA_DIR="$HOME/agilex/data_umi202/"
# 任务类型
TASK_TYPE="single_pika"
# ===========================================

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ------------------------------------------------------------------
# [针对你的环境修复] 显式加载位于 /opt/conda 的初始化文件
# ------------------------------------------------------------------
CONDA_SHELL_SCRIPT="/opt/conda/etc/profile.d/conda.sh"

if [ -f "$CONDA_SHELL_SCRIPT" ]; then
    source "$CONDA_SHELL_SCRIPT"
else
    log_err "找不到 Conda 初始化文件: $CONDA_SHELL_SCRIPT"
    exit 1
fi


log_info() { echo -e "${GREEN}[INFO] $1${NC}"; }
log_warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
log_err()  { echo -e "${RED}[ERROR] $1${NC}"; }

# 检查路径
if [ ! -d "$PIKA_WS" ]; then
    log_err "找不到项目路径: $PIKA_WS"
    exit 1
fi

# 确保 ROS2 环境已加载
if [ -f "$PIKA_WS/install/setup.bash" ]; then
    source "$PIKA_WS/install/setup.bash"
else
    log_err "找不到 ROS2 setup.bash，请先编译工作空间。"
    exit 1
fi

echo "----------------------------------------------------"
echo -e "${YELLOW}       Pika Bot 数据处理流水线       ${NC}"
echo "----------------------------------------------------"
echo "即将执行以下步骤："
echo "1. 数据同步 (ros2 run_data_sync)"
echo "2. 转换为 HDF5 (data_to_hdf5.py)"
echo "3. 转换为 LeRobot 格式 (convert_to_lerobot.sh)"
echo "----------------------------------------------------"
read -p "按回车键开始处理，或按 Ctrl+C 取消..."

# --- 步骤 1: 数据同步 ---
log_info "STEP 1/3: 开始数据同步..."

source /mnt/nas/projects/robot/pika_ros/install/setup.sh 
ros2 launch data_tools run_data_sync.launch.py \
    type:="$TASK_TYPE" \
    datasetDir:="$DATA_DIR" \
    episodeIndex:=-1

# 检查上一条命令是否成功 ($? 等于 0 表示成功)
if [ $? -ne 0 ]; then
    log_err "数据同步失败，流程终止。"
    exit 1
fi
log_info "数据同步完成。"

# --- 步骤 2: 数据转换 (HDF5) ---
log_info "STEP 2/3: 开始转换为 HDF5..."
cd "$PIKA_WS/scripts" || exit 1

conda activate pika

python3 /mnt/nas/projects/robot/pika_ros/scripts/data_to_hdf5.py \
    --type "$TASK_TYPE" \
    --datasetDir "$DATA_DIR" \
    --useCameraPointCloud ""

if [ $? -ne 0 ]; then
    log_err "HDF5 转换失败，流程终止。"
    exit 1
fi

conda deactivate

log_info "HDF5 转换完成。"

# --- 步骤 3: 转换为 LeRobot ---
log_info "STEP 3/3: 开始转换为 LeRobot 格式..."

# 检查脚本是否有执行权限，如果没有则添加
# if [ ! -x "convert_to_lerobot.sh" ]; then
#     chmod +x convert_to_lerobot.sh
# fi

conda activate lerobot

python3 /mnt/nas/projects/robot/pika_ros/convert_to_lerobot.py

if [ $? -ne 0 ]; then
    log_err "LeRobot 转换失败。"
    exit 1
fi

conda deactivate

echo "----------------------------------------------------"
log_info "🎉 所有数据处理步骤已成功完成！"
echo "----------------------------------------------------"