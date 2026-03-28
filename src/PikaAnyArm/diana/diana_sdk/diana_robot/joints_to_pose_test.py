import DianaApi
import math  # 1. 引入 math 库用于计算角度

# 配置 IP 地址
ipAddress = '192.168.10.76'  # 请替换为实际 IP

# 初始化服务
srv_net_st = [ipAddress, 5001, 5002, 5003, 5004, 5005]
DianaApi.initSrv(srv_net_st)        

# 定义变量
JOINT_NUM = 7
joints = [0.0] * JOINT_NUM
tcp_pose = [0.0] * 6

try:
    # 2. 获取当前关节角度
    DianaApi.getJointPos(joints, ipAddress)
    print("Joint pos (rad):", joints)
    
    # 3. 计算正解 (Forward Kinematics)
    # forward 计算出的 tcp_pose 默认格式为 [x, y, z, rx(rad), ry(rad), rz(rad)]
    is_success = DianaApi.forward(joints, tcp_pose, ipAddress)

    # 4. 转换并输出
    if is_success:
        # 创建一个新的列表用于存放转换后的数据
        tcp_pose_deg = list(tcp_pose) # 复制一份数据
        
        # 将 Rx, Ry, Rz (索引 3, 4, 5) 转换为度数
        tcp_pose_deg[3] = math.degrees(tcp_pose[3])
        tcp_pose_deg[4] = math.degrees(tcp_pose[4])
        tcp_pose_deg[5] = math.degrees(tcp_pose[5])
        
        print("-" * 30)
        print("Calculated TCP Pose (Rx/Ry/Rz in Degrees):")
        print(tcp_pose_deg)
        print(tcp_pose)
        print(DianaApi.getTcpPos(tcp_pose, ipAddress))
        print(tcp_pose)
        DianaApi.releaseBrake(ipAddress)
        tcp_pose[5] += 0.1
        DianaApi.moveL(tcp_pose, v=0.1, a=0.1, ipAddress=ipAddress)
        import time
        time.sleep(1.0)
        # 如果你想看更直观的格式，可以这样打印：
        print(f"X: {tcp_pose_deg[0]:.4f}, Y: {tcp_pose_deg[1]:.4f}, Z: {tcp_pose_deg[2]:.4f}")
        print(f"Rx: {tcp_pose_deg[3]:.4f}°, Ry: {tcp_pose_deg[4]:.4f}°, Rz: {tcp_pose_deg[5]:.4f}°")
    else:
        print("Forward calculation failed.")

finally:
    # 5. 释放资源
    DianaApi.destroySrv()