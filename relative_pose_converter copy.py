#!/usr/bin/env python3
# -- coding: UTF-8
"""
将绝对 6DoF 位姿序列转换为 UMI 扩散策略所需的两类相对 SE(3) 位姿：
1) t0 -> t 的相对位姿，作为去噪条件；
2) t -> t+1 的相对位姿，作为监督标签。

核心特点
- 输入为“平移 + 欧拉角 (roll, pitch, yaw)”的 JSON 序列。
- 输出为“平移 + 单位四元数”，避免欧拉角奇异与累积漂移。
- 自动在原始位姿目录的上一层创建两个结果文件夹，保持文件名对齐。
- 提供小型自测用例，可直接运行验证几何正确性。
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.spatial.transform import Rotation as R


# -------------------------- 几何与格式工具函数 -------------------------- #

def _pose_dict_to_matrix(pose: Dict[str, float]) -> np.ndarray:
    """将单条 pose 字典转为 4x4 齐次变换矩阵。
    说明：统一使用 xyz 平移 + R.from_euler('xyz')，假设 roll/pitch/yaw 已为弧度。
    """
    required = {"x", "y", "z", "roll", "pitch", "yaw"}
    missing = required - pose.keys()
    if missing:
        raise ValueError(f"缺失字段: {missing}")

    translation = np.array([pose["x"], pose["y"], pose["z"]], dtype=float)
    rot_matrix = R.from_euler("xyz", [pose["roll"], pose["pitch"], pose["yaw"]]).as_matrix()

    T = np.eye(4)
    T[:3, :3] = rot_matrix
    T[:3, 3] = translation
    return T


def _matrix_to_trans_quat(T: np.ndarray) -> Dict[str, float]:
    """将 4x4 齐次矩阵转为“平移 + 四元数”，并强制单位化避免数值漂移。"""
    quat = R.from_matrix(T[:3, :3]).as_quat()  # xyzw
    quat = quat / np.linalg.norm(quat)
    return {
        "x": float(T[0, 3]),
        "y": float(T[1, 3]),
        "z": float(T[2, 3]),
        "qx": float(quat[0]),
        "qy": float(quat[1]),
        "qz": float(quat[2]),
        "qw": float(quat[3]),
    }


def _load_pose_sequence(abs_pose_dir: Path) -> Tuple[List[np.ndarray], List[Path]]:
    """读取并按文件名排序位姿序列。
    - 用文件名作为时间戳排序，保证时序一致；
    - 遇到损坏/缺字段文件时跳过并提示，提升鲁棒性。
    """
    def _sort_key(p: Path):
        try:
            return float(p.stem)
        except ValueError:
            return p.stem

    pose_files = sorted(abs_pose_dir.glob("*.json"), key=_sort_key)
    transforms, kept_files = [], []
    for f in pose_files:
        try:
            data = json.loads(f.read_text())
            T = _pose_dict_to_matrix(data)
            transforms.append(T)
            kept_files.append(f)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 跳过文件 {f.name}: {exc}")
    if len(transforms) < 2:
        raise RuntimeError(f"{abs_pose_dir} 中有效位姿不足 2 条，无法计算相对变换")
    return transforms, kept_files


# --------------------------- 相对位姿计算 --------------------------- #

def _relative_to_t0(T_abs: List[np.ndarray]) -> List[np.ndarray]:
    """计算每个时刻相对于首帧 t0 的位姿（t0->t）。"""
    T0_inv = np.linalg.inv(T_abs[0])
    return [T0_inv @ Tt for Tt in T_abs]


def _relative_to_next(T_abs: List[np.ndarray], keep_last_identity: bool = True) -> List[np.ndarray]:
    """计算相对于下一时刻的位姿（t->t+1）。
    - 为了对齐帧数，默认最后一帧写入单位阵（代表“无后续”），便于后续按原长度索引。
    """
    rel = []
    for i in range(len(T_abs) - 1):
        rel.append(np.linalg.inv(T_abs[i]) @ T_abs[i + 1])
    if keep_last_identity:
        rel.append(np.eye(4))
    return rel


# ----------------------------- 主流程 ----------------------------- #

def convert_abs_to_relative(
    abs_pose_dir: Path,
    overwrite: bool = False,
    keep_last_identity: bool = True,
) -> Tuple[Path, Path]:
    """核心转换入口。

    参数
    - abs_pose_dir: 绝对位姿文件夹（形如 .../pose/pika）
    - overwrite: 结果存在时是否覆盖
    - keep_last_identity: 是否为最后一帧补单位阵，保持长度一致
    """
    if not abs_pose_dir.exists():
        raise FileNotFoundError(f"未找到输入目录: {abs_pose_dir}")

    T_abs, pose_files = _load_pose_sequence(abs_pose_dir)

    # 输出目录：位于上一层 pose 目录，按要求分成两类并保留机器人子目录
    parent_dir = abs_pose_dir.parent
    robot_name = abs_pose_dir.name
    out_t0_dir = parent_dir / "relative_to_t0" / robot_name
    out_next_dir = parent_dir / "relative_to_next" / robot_name

    for d in (out_t0_dir, out_next_dir):
        if d.exists():
            if not overwrite:
                raise FileExistsError(f"输出目录已存在: {d}，如需覆盖请使用 --overwrite")
            # 先清空旧结果，避免帧数减少时留下过期文件
            for old in d.rglob("*.json"):
                old.unlink()
        d.mkdir(parents=True, exist_ok=True)

    # 计算相对变换
    rel_t0 = _relative_to_t0(T_abs)
    rel_next = _relative_to_next(T_abs, keep_last_identity=keep_last_identity)

    # 写出 JSON，文件名与原始对齐，便于后续同步
    for T, src in zip(rel_t0, pose_files):
        (out_t0_dir / src.name).write_text(json.dumps(_matrix_to_trans_quat(T), ensure_ascii=False, indent=2))

    for T, src in zip(rel_next, pose_files):
        (out_next_dir / src.name).write_text(json.dumps(_matrix_to_trans_quat(T), ensure_ascii=False, indent=2))

    print(f"[OK] 共处理 {len(pose_files)} 帧，结果已写入:\n- {out_t0_dir}\n- {out_next_dir}")
    return out_t0_dir, out_next_dir


# ----------------------------- 示例与测试 ----------------------------- #

def _build_demo_sequence(root: Path) -> Path:
    """构造一个三帧的可重复测试序列，便于快速 sanity check。"""
    abs_dir = root / "episode_demo" / "localization" / "pose" / "pika"
    abs_dir.mkdir(parents=True, exist_ok=True)
    demo_poses = [
        # t0: 原点朝向 0
        {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        # t1: 沿 x 前进 0.1，绕 z 旋转 90 度
        {"x": 0.1, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": math.pi / 2},
        # t2: 在 t1 坐标系再向 y 正方向移动 0.1，绕 z 再转 90 度（累积朝向 180°）
        {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": math.pi},
    ]
    for idx, pose in enumerate(demo_poses):
        ts_name = f"177003759{idx}.json"  # 仿造原始时间戳命名
        (abs_dir / ts_name).write_text(json.dumps(pose, ensure_ascii=False, indent=2))
    return abs_dir


def _run_self_test():
    """简单几何单元测试，验证相对计算与四元数结果是否合理。"""
    temp_root = Path("/tmp/relative_pose_test")
    if temp_root.exists():
        # 避免干扰之前的测试结果
        for p in temp_root.rglob("*.json"):
            p.unlink()
    abs_dir = _build_demo_sequence(temp_root)
    out_t0, out_next = convert_abs_to_relative(abs_dir, overwrite=True, keep_last_identity=True)

    # 读取结果做数值校验
    rel_t0_files = sorted(out_t0.glob("*.json"))
    rel_next_files = sorted(out_next.glob("*.json"))

    def _load(path: Path):
        with path.open() as f:
            return json.load(f)

    t0 = [_load(f) for f in rel_t0_files]
    tn = [_load(f) for f in rel_next_files]

    # t0->t1 应为平移 (0.1, 0, 0) + yaw 90°
    assert np.allclose([t0[1]["x"], t0[1]["y"]], [0.1, 0.0], atol=1e-6)
    yaw_90 = R.from_quat([t0[1]["qx"], t0[1]["qy"], t0[1]["qz"], t0[1]["qw"]]).as_euler("xyz")[2]
    assert math.isclose(yaw_90, math.pi / 2, rel_tol=1e-4)

    # t1->t2 应在 t1 坐标系下沿 y 正向 0.1，且再转 90°
    assert np.allclose([tn[1]["x"], tn[1]["y"]], [0.0, 0.1], atol=1e-6)
    yaw_delta = R.from_quat([tn[1]["qx"], tn[1]["qy"], tn[1]["qz"], tn[1]["qw"]]).as_euler("xyz")[2]
    assert math.isclose(yaw_delta, math.pi / 2, rel_tol=1e-4)

    # 最后一帧被补单位阵
    assert np.allclose([tn[-1]["x"], tn[-1]["y"], tn[-1]["z"]], [0, 0, 0], atol=1e-8)

    print("✅ 自测通过：示例序列的相对位姿计算正确。")


# ----------------------------- CLI 入口 ----------------------------- #

def parse_args():
    parser = argparse.ArgumentParser(description="将绝对位姿 JSON 序列转换为相对 SE(3)（t0->t 与 t->t+1）。")
    parser.add_argument(
        "--abs-pose-dir",
        type=Path,
        required=False,
        default=None,
        help="绝对位姿所在目录，例如 /home/robot/agilex/data_umi202/episode0/localization/pose/pika",
    )
    parser.add_argument("--overwrite", action="store_true", help="若输出目录已存在则覆盖")
    parser.add_argument(
        "--drop-last",
        dest="keep_last_identity",
        action="store_false",
        default=True,
        help="若设置，则不为最后一帧补单位阵（默认补单位阵以保持帧数一致）",
    )
    parser.add_argument(
        "--run-self-test",
        action="store_true",
        help="运行内置示例并验证结果，无需提供 abs-pose-dir",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.run_self_test:
        _run_self_test()
        return
    if args.abs_pose_dir is None:
        raise SystemExit("请通过 --abs-pose-dir 指定绝对位姿目录，或使用 --run-self-test 运行示例")

    convert_abs_to_relative(
        abs_pose_dir=args.abs_pose_dir,
        overwrite=args.overwrite,
        keep_last_identity=args.keep_last_identity,
    )


if __name__ == "__main__":
    main()
