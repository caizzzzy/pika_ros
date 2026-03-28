import os
import json
import DianaApi
import time
from pika_remote_diana.tools import MATHTOOLS

# ================= 配置区域 =================
# 机器人 IP 地址
IP_ADDRESS = '192.168.10.76'

# 数据根目录 (包含 episode1, episode2, ... 等文件夹的父级目录)
DATA_ROOT = '/home/robot/agilex/data0204/'

# 文件夹内部相对路径配置
# 输入数据的相对路径
REL_INPUT_PATH = 'arm/jointState/puppet/'
# 输出数据的相对路径
REL_OUTPUT_PATH = 'arm/endPose/puppet/'

# 关节数量
JOINT_NUM = 7
tools = MATHTOOLS()
# ===========================================

def process_episode(episode_name, episode_path, total_success, total_fail):
    """
    处理单个 episode 文件夹的函数
    """
    # 拼接完整的输入和输出目录路径
    input_dir = os.path.join(episode_path, REL_INPUT_PATH)
    output_dir = os.path.join(episode_path, REL_OUTPUT_PATH)

    # 检查该 episode 是否包含目标输入目录
    if not os.path.exists(input_dir):
        # 如果这个文件夹没有 input 结构，跳过（可能不是数据文件夹）
        # print(f"跳过 {episode_name}: 找不到路径 {input_dir}")
        return total_success, total_fail

    print(f"正在处理文件夹: {episode_name} ...")

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"  [错误] 创建输出目录失败: {e}")
            return total_success, total_fail

    # 获取该目录下所有 JSON 文件
    files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    if not files:
        print(f"  [警告] {episode_name} 中没有 JSON 文件。")
        return total_success, total_fail

    local_success = 0
    local_fail = 0

    for filename in files:
        input_file_path = os.path.join(input_dir, filename)
        output_file_path = os.path.join(output_dir, filename)

        try:
            # 读取 JSON
            with open(input_file_path, 'r') as f:
                data = json.load(f)

            # 校验数据
            if 'position' not in data or len(data['position']) != JOINT_NUM:
                print(f"  [跳过] 文件 {filename} 格式错误")
                local_fail += 1
                continue

            joints = data['position']
            tcp_pose = [0.0] * 6

            # 计算正解 (Forward Kinematics)
            is_success = DianaApi.forward(joints, tcp_pose, IP_ADDRESS)

            if is_success:
                # 转换数据格式: rx,ry,rz -> roll, pitch, yaw
                # DianaApi 输出顺序: [x, y, z, rx, ry, rz]
                roll, pitch, yaw = tools.rotvec_to_rpy(tcp_pose[3:6])
                output_data = {
                    "pitch": pitch, # ry
                    "roll": roll,  # rx
                    "x": tcp_pose[0],
                    "y": tcp_pose[1],
                    "yaw": yaw,   # rz
                    "z": tcp_pose[2]
                }

                # 写入文件
                with open(output_file_path, 'w') as out_f:
                    json.dump(output_data, out_f, indent=4, sort_keys=True)
                
                local_success += 1
            else:
                print(f"  [失败] 正解计算失败: {filename}")
                local_fail += 1

        except Exception as e:
            print(f"  [异常] 处理文件 {filename} 时出错: {e}")
            local_fail += 1

    print(f"  -> {episode_name} 完成。成功: {local_success}, 失败: {local_fail}")
    return total_success + local_success, total_fail + local_fail

def main():
    # 1. 初始化 DianaApi 服务
    print(f"正在连接机器人服务: {IP_ADDRESS} ...")
    srv_net_st = [IP_ADDRESS, 5001, 5002, 5003, 5004, 5005]
    DianaApi.initSrv(srv_net_st)

    total_success = 0
    total_fail = 0

    try:
        # 2. 检查根目录
        if not os.path.exists(DATA_ROOT):
            print(f"错误: 找不到数据根目录 {DATA_ROOT}")
            return

        # 3. 获取根目录下所有项目 (episode1, episode2, ...)
        # 按照文件名排序，这样处理顺序比较直观
        items = sorted(os.listdir(DATA_ROOT))
        
        print(f"开始扫描 {DATA_ROOT} 下的所有目录...")

        for item in items:
            item_path = os.path.join(DATA_ROOT, item)
            
            # 确保是文件夹
            if os.path.isdir(item_path):
                # 调用处理函数
                total_success, total_fail = process_episode(item, item_path, total_success, total_fail)

    finally:
        # 4. 释放资源
        print("=" * 40)
        print(f"所有任务处理完成。")
        print(f"总成功文件数: {total_success}")
        print(f"总失败文件数: {total_fail}")
        print("断开 DianaApi 服务连接...")
        DianaApi.destroySrv()

if __name__ == "__main__":
    main()