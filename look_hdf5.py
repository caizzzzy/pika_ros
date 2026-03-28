import h5py
import numpy as np

# ========== 替换为你的HDF5文件路径 ==========
h5_file_path = "/home/robot/agilex/data_umi0321/episode0/data.hdf5"

# 1. 打开HDF5文件（只读模式）
with h5py.File(h5_file_path, "r") as f:
    print("="*50)
    print("HDF5文件内所有字段（按层级展示）：")
    print("="*50)
    
    # 递归打印所有字段（含层级）
    def print_hdf5_structure(name, obj):
        if isinstance(obj, h5py.Dataset):
            # 打印字段名、形状、数据类型
            print(f"字段：{name} | 形状：{obj.shape} | 数据类型：{obj.dtype}")
        elif isinstance(obj, h5py.Group):
            print(f"分组：{name}")
    
    f.visititems(print_hdf5_structure)

    print("\n" + "="*50)
    print("关键字段数据示例（相对位姿）：")
    print("="*50)
    
    # 2. 查看relative_to_t0的前3帧数据（适配你的场景）
    if "localization/relative_to_t0/pika" in f:
        rel_t0_data = f["localization/relative_to_t0/pika"][:3]  # 读取前3帧
        print("relative_to_t0/pika 前3帧数据（x,y,z,qx,qy,qz,qw）：")
        print(rel_t0_data)
    
    # 3. 查看relative_to_next的前3帧数据
    if "localization/relative_to_next/pika" in f:
        rel_next_data = f["localization/relative_to_next/pika"][:3]
        print("\nrelative_to_next/pika 前3帧数据：")
        print(rel_next_data)
    
    # 4. 查看时间戳和总帧数
    if "timestamp" in f:
        print("\n前3个时间戳：", f["timestamp"][:3])
    if "size" in f:
        print("总帧数：", f["size"][()])  # 单个值需加[()]读取