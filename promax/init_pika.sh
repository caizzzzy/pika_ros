#!/bin/bash

# ================= 配置区域 =================
# 将基础路径修改为你的实际绝对路径
PIKA_WS="/mnt/nas/projects/robot/pika_ros"
# ===========================================

# 定义颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO] $1${NC}"; }
log_warn() { echo -e "${YELLOW}[WARN] $1${NC}"; }
log_err()  { echo -e "${RED}[ERROR] $1${NC}"; }

# 检查工作空间是否存在
if [ ! -d "$PIKA_WS" ]; then
    log_err "关键路径不存在: $PIKA_WS"
    log_err "请检查 NAS 是否挂载或路径是否正确。"
    exit 1
fi

# 主循环
while true; do
    echo "----------------------------------------------------"
    echo -e "${YELLOW}       Pika Bot 初始化流程控制台       ${NC}"
    echo "       当前路径: $PIKA_WS"
    echo "----------------------------------------------------"
    echo "1. 配置 USB 规则 (需 sudo 权限 + 手动拔插)"
    echo "2. 定位基站校准 (Survive Calibrate)"
    echo "3. 绑定设备 (Setup Device)"
    echo "4. 退出 (Exit)"
    echo "----------------------------------------------------"
    read -p "请输入选项 [1-4]: " choice

    case $choice in
        1)
            # 步骤 1: 配置 USB 规则
            log_info "正在配置 USB 规则..."
            RULES_FILE="$PIKA_WS/scripts/81-vive.rules"
            
            if [ -f "$RULES_FILE" ]; then
                # 复制规则文件
                sudo cp "$RULES_FILE" /etc/udev/rules.d/
                # 重载规则
                sudo udevadm control --reload-rules && sudo udevadm trigger
                
                log_info "规则已重载。"
                log_warn "【重要】请现在重新拔插接收器！"
                read -p "拔插完成后，请按回车键继续..."
            else
                log_err "未找到规则文件: $RULES_FILE"
            fi
            ;;
            
        2)
            # 步骤 2: 定位基站校准
            log_info "正在启动基站校准..."
            CALIB_DIR="$PIKA_WS/install/libsurvive/bin"
            
            if [ -d "$CALIB_DIR" ]; then
                cd "$CALIB_DIR" || exit
                ./survive-cli --force-calibrate
                # 执行完不需要手动切回，下一次循环会自动定位路径
            else
                log_err "未找到校准目录: $CALIB_DIR"
            fi
            ;;
            
        3)
            # 步骤 3: 绑定设备
            log_info "正在绑定设备..."
            SCRIPT_DIR="$PIKA_WS/scripts"
            
            if [ -d "$SCRIPT_DIR" ]; then
                cd "$SCRIPT_DIR" || exit
                
                log_info "执行 setup_device.py..."
                # 注意：如果你之前是在 conda 环境下，这里可能需要确保使用正确的 python
                # 如果 setup_device.py 需要系统 python (非 conda)，建议写成 /usr/bin/python3
                python3 setup_device.py
            else
                log_err "未找到脚本目录: $SCRIPT_DIR"
            fi
            ;;
            
        4)
            log_info "退出初始化流程。"
            exit 0
            ;;
            
        *)
            log_err "无效输入，请输入 1-4。"
            ;;
    esac

    echo ""
    read -p "本步骤执行完毕，按回车键返回主菜单..."
done
