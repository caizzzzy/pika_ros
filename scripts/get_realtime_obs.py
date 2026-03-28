#!/usr/bin/env python3
"""
Collect a single observation for real‑time inference with the same preprocessing
used in convert_to_lerobot.py / LeRobot training:
  - state = arm joint positions + gripper distance (concatenate)
  - state normalization = (x - mean) / std from dataset stats.json
  - image normalization = ImageNet (default) or dataset stats
Fill `observation.state` and `observation.images.cam_high` just like the dataset.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from data_msgs.msg import Gripper
from cv_bridge import CvBridge, CvBridgeError

# Default image normalization used by LeRobot when ImageNet stats are injected
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def load_stats(stats_path: Path) -> Dict:
    if not stats_path.exists():
        raise FileNotFoundError(f"stats.json not found: {stats_path}")
    with stats_path.open("r") as f:
        return json.load(f)


class ObsCollector(Node):
    def __init__(
        self,
        image_topic: str,
        joint_topic: str,
        gripper_topic: str,
        stats_path: Path,
        use_dataset_image_stats: bool,
        image_encoding: str = "bgr8",
    ):
        super().__init__("lerobot_obs_collector")
        self.bridge = CvBridge()
        self.image_encoding = image_encoding

        stats = load_stats(stats_path)
        state_stats = stats.get("observation.state", {})
        self.state_mean = np.array(state_stats.get("mean", []), dtype=np.float32)
        self.state_std = np.array(state_stats.get("std", []), dtype=np.float32)
        self.state_std[self.state_std == 0] = 1e-6

        if use_dataset_image_stats:
            # stats key follows convert_to_lerobot naming: observation.images.cam_high
            img_stats = next((v for k, v in stats.items() if k.startswith("observation.images.")), None)
            if img_stats:
                mean = torch.tensor(img_stats.get("mean", IMAGENET_MEAN.tolist())).view(3, 1, 1)
                std = torch.tensor(img_stats.get("std", IMAGENET_STD.tolist())).view(3, 1, 1)
                self.img_mean = mean
                self.img_std = torch.clamp(std, min=1e-6)
            else:
                self.img_mean, self.img_std = IMAGENET_MEAN, IMAGENET_STD
        else:
            self.img_mean, self.img_std = IMAGENET_MEAN, IMAGENET_STD

        self.latest_image: Optional[np.ndarray] = None
        self.latest_joint: Optional[np.ndarray] = None
        self.latest_gripper: Optional[float] = None

        self.create_subscription(Image, image_topic, self._image_cb, 10)
        self.create_subscription(JointState, joint_topic, self._joint_cb, 10)
        self.create_subscription(Gripper, gripper_topic, self._gripper_cb, 10)

        self.get_logger().info(
            f"Listening -> image: {image_topic}, joint: {joint_topic}, gripper: {gripper_topic}"
        )

    # --- ROS callbacks -----------------------------------------------------
    def _image_cb(self, msg: Image):
        try:
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.image_encoding)
            self.latest_image = img
        except CvBridgeError as e:
            self.get_logger().warning(f"Image conversion failed: {e}")

    def _joint_cb(self, msg: JointState):
        self.latest_joint = np.array(msg.position, dtype=np.float32)

    def _gripper_cb(self, msg: Gripper):
        self.latest_gripper = float(msg.distance)

    # --- Public API --------------------------------------------------------
    def ready(self) -> bool:
        return self.latest_image is not None and self.latest_joint is not None and self.latest_gripper is not None

    def build_obs(self) -> Optional[Dict[str, torch.Tensor]]:
        if not self.ready():
            return None

        state = np.concatenate([self.latest_joint, [self.latest_gripper]]).astype(np.float32)
        if len(self.state_mean) == state.shape[0]:
            norm_state = (state - self.state_mean) / self.state_std
        else:
            self.get_logger().warning(
                f"State dim mismatch (got {state.shape[0]}, expected {len(self.state_mean)}); skipping normalization"
            )
            norm_state = state

        img = torch.from_numpy(self.latest_image).to(torch.float32) / 255.0
        # BGR from CvBridge; stay consistent with saved dataset frames (captured via cv2).
        img = img.permute(2, 0, 1)  # HWC -> CHW
        norm_img = (img - self.img_mean) / self.img_std

        obs = {
            "observation.state": torch.from_numpy(norm_state),
            "observation.images.cam_high": norm_img,
        }
        return obs


def parse_args():
    parser = argparse.ArgumentParser(description="Collect one preprocessed obs for LeRobot policy inference.")
    parser.add_argument("--stats", type=Path, default=Path("lerobot_dataset_agilex/meta/stats.json"),
                        help="Path to stats.json generated by convert_to_lerobot.py")
    parser.add_argument("--image-topic", type=str, default="/gripper/camera/color/image_raw")
    parser.add_argument("--joint-topic", type=str, default="/joint_states_single_gripper")
    parser.add_argument("--gripper-topic", type=str, default="/sensor/gripper/data")
    parser.add_argument("--image-encoding", type=str, default="bgr8",
                        help="Desired encoding passed to CvBridge (keep bgr8 to match recorded PNGs).")
    parser.add_argument("--use-dataset-image-stats", action="store_true",
                        help="Use stats.json image mean/std instead of ImageNet defaults.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for all topics before giving up.")
    return parser.parse_args()


def main():
    args = parse_args()
    rclpy.init()
    node = ObsCollector(
        image_topic=args.image_topic,
        joint_topic=args.joint_topic,
        gripper_topic=args.gripper_topic,
        stats_path=args.stats,
        use_dataset_image_stats=args.use_dataset_image_stats,
        image_encoding=args.image_encoding,
    )

    try:
        deadline = node.get_clock().now().nanoseconds + int(args.timeout * 1e9)
        obs = None
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            obs = node.build_obs()
            if obs is not None:
                break
            if node.get_clock().now().nanoseconds > deadline:
                node.get_logger().error("Timed out waiting for all topics.")
                break

        if obs is not None:
            state = obs["observation.state"]
            img = obs["observation.images.cam_high"]
            node.get_logger().info(
                f"Obs ready -> state shape: {tuple(state.shape)}, image shape: {tuple(img.shape)}, "
                f"state mean: {state.mean().item():.3f}, image mean: {img.mean().item():.3f}"
            )
            # Example: feed to your policy here
            # action = policy(obs)  # obs keys match dataset feature names
        else:
            node.get_logger().error("No observation built; check incoming topics.")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
