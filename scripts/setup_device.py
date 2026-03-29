#!/usr/bin/env python3

import os
import re
import subprocess
import time

import cv2


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_project_root():
    current = SCRIPT_DIR
    while True:
        if os.path.isdir(os.path.join(current, "start_pika")) and os.path.isdir(os.path.join(current, "scripts")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return SCRIPT_DIR
        current = parent


PROJECT_ROOT = find_project_root()
START_PIKA_DIR = os.path.join(PROJECT_ROOT, "start_pika")
START_PIKA_DEVICE_CONFIG = os.path.join(START_PIKA_DIR, "single_arm_sensor_2grippers_device_config.bash")


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"执行命令时出错: {str(e)}")
        return None


def write_executable(path, content):
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o755)


def get_device_info():
    rs_output = run_command("rs-enumerate-devices -s")
    if not rs_output:
        print("无法获取到深度摄像头数据")
        return None, None

    serial_match = re.search(r"Intel RealSense D405\s+(\d+)", rs_output)
    if not serial_match:
        print("无法获取到深度摄像头数据")
        return None, None
    serial_number = serial_match.group(1)

    ls_output = run_command("ls /dev | grep ttyUSB | grep -v ttyUSB50 | grep -v ttyUSB51 | grep -v ttyUSB60 | grep -v ttyUSB61")
    count = ls_output.count("tty")
    if count > 1:
        print("请确保工控机只插入一个USB串口设备")
        return None, None
    udev_output = run_command(f"udevadm info /dev/{ls_output} | grep DEVPATH")
    if not udev_output:
        print("无法获取到串口数据")
        return None, None

    usb_path = udev_output[:udev_output.find(ls_output)][:-1]
    usb_path = usb_path[usb_path.rfind("/") + 1:]

    print("寻找鱼眼摄像头，请在出现鱼眼摄像头时按下s，非鱼眼摄像头则按下q(注意在图像窗口按下，不要在终端！！！)")
    video_path = None
    cv2.setLogLevel(0)
    for i in range(50):
        cap = cv2.VideoCapture(i)
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        key = None
        if cap.isOpened():
            while True:
                ret, frame = cap.read()
                cv2.imshow("/dev/video" + str(i), frame)
                key = cv2.waitKey(1)
                if key & 0xFF == ord("q"):
                    break
                elif key & 0xFF == ord("s"):
                    break
        cv2.destroyAllWindows()
        if key is not None and key & 0xFF == ord("s"):
            video_path = "video" + str(i)
            break
    cv2.destroyAllWindows()
    if video_path is None:
        print("无法获取到鱼眼摄像头数据")
        return None, None

    udev_output = run_command(f"udevadm info /dev/{video_path} | grep DEVPATH")
    video_path = udev_output[:udev_output.find("video")][:-1]
    video_path = video_path[video_path.rfind("/") + 1:]

    return serial_number, usb_path, video_path


def generate_setup_bash(left_info, right_info, select, third_info=None):
    if select == "1":
        path = "setup_multi_sensor.bash"
        content = f"""
#/bin/bash

sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{left_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB50\\"" > /etc/udev/rules.d/sensor_serial.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{right_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB51\\"" >> /etc/udev/rules.d/sensor_serial.rules'

sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{left_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video50\\"" > /etc/udev/rules.d/sensor_fisheye.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{right_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video51\\"" >> /etc/udev/rules.d/sensor_fisheye.rules'

sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger
"""
    elif select == "2":
        path = "setup_multi_gripper.bash"
        content = f"""
#/bin/bash

sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{left_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB60\\"" > /etc/udev/rules.d/gripper_serial.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{right_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB61\\"" >> /etc/udev/rules.d/gripper_serial.rules'

sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{left_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video60\\"" > /etc/udev/rules.d/gripper_fisheye.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{right_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video61\\"" >> /etc/udev/rules.d/gripper_fisheye.rules'

sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger
"""
    elif select == "3":
        path = "setup_sensor_gripper.bash"
        content = f"""
#/bin/bash

sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{left_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB50\\"" > /etc/udev/rules.d/sensor_serial.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{right_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB60\\"" > /etc/udev/rules.d/gripper_serial.rules'

sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{left_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video50\\"" > /etc/udev/rules.d/sensor_fisheye.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{right_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video60\\"" > /etc/udev/rules.d/gripper_fisheye.rules'

sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger
"""
    else:
        path = "setup_sensor_2grippers_global_camera.bash"
        content = f"""
#/bin/bash

sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{left_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB50\\"" > /etc/udev/rules.d/sensor_serial.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{right_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB60\\"" > /etc/udev/rules.d/gripper_serial.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNELS==\\"{third_info[1]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"ttyUSB61\\"" >> /etc/udev/rules.d/gripper_serial.rules'

sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{left_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video50\\"" > /etc/udev/rules.d/sensor_fisheye.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{right_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video60\\"" > /etc/udev/rules.d/gripper_fisheye.rules'
sudo sh -c 'echo "ACTION==\\"add\\", KERNEL==\\"video[0,2,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48]*\\", KERNELS==\\"{third_info[2]}\\", SUBSYSTEMS==\\"usb\\", MODE:=\\"0777\\", SYMLINK+=\\"video61\\"" >> /etc/udev/rules.d/gripper_fisheye.rules'

sudo udevadm control --reload-rules && sudo service udev restart && sudo udevadm trigger
"""

    write_executable(path, content)
    return path


def generate_start_bash(left_info, right_info, select):
    if select == "1":
        path = "start_multi_sensor.bash"
        content = f"""
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
camera_fps=30
camera_width=640
camera_height=480
l_depth_camera_no={left_info[0]}
r_depth_camera_no={right_info[0]}

l_serial_port=/dev/ttyUSB50
r_serial_port=/dev/ttyUSB51
sudo chmod a+rw /dev/ttyUSB*
l_fisheye_port=50
r_fisheye_port=51
sudo chmod a+rw /dev/video*

source /opt/ros/humble/setup.bash && cd $SCRIPT_DIR/../install/sensor_tools/share/sensor_tools/scripts/ && chmod 777 usb_camera.py
if [ -n "$1" ]; then
    source $SCRIPT_DIR/../install/setup.bash && ros2 launch sensor_tools open_multi_sensor.launch.py l_depth_camera_no:=_$l_depth_camera_no r_depth_camera_no:=_$r_depth_camera_no l_serial_port:=$l_serial_port r_serial_port:=$r_serial_port l_fisheye_port:=$l_fisheye_port r_fisheye_port:=$r_fisheye_port camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps name:=$1 name_index:=$1_
else
    source $SCRIPT_DIR/../install/setup.bash && ros2 launch sensor_tools open_multi_sensor.launch.py l_depth_camera_no:=_$l_depth_camera_no r_depth_camera_no:=_$r_depth_camera_no l_serial_port:=$l_serial_port r_serial_port:=$r_serial_port l_fisheye_port:=$l_fisheye_port r_fisheye_port:=$r_fisheye_port camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps
fi
"""
    elif select == "2":
        path = "start_multi_gripper.bash"
        content = f"""
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
camera_fps=30
camera_width=640
camera_height=480
l_depth_camera_no={left_info[0]}
r_depth_camera_no={right_info[0]}

l_serial_port=/dev/ttyUSB60
r_serial_port=/dev/ttyUSB61
sudo chmod a+rw /dev/ttyUSB*
l_fisheye_port=60
r_fisheye_port=61
sudo chmod a+rw /dev/video*

source /opt/ros/humble/setup.bash && cd $SCRIPT_DIR/../install/sensor_tools/share/sensor_tools/scripts/ && chmod 777 usb_camera.py
if [ -n "$1" ]; then
    source $SCRIPT_DIR/../install/setup.bash && ros2 launch sensor_tools open_multi_gripper.launch.py l_depth_camera_no:=_$l_depth_camera_no r_depth_camera_no:=_$r_depth_camera_no l_serial_port:=$l_serial_port r_serial_port:=$r_serial_port l_fisheye_port:=$l_fisheye_port r_fisheye_port:=$r_fisheye_port camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps name:=$1 name_index:=$1_
else
    source $SCRIPT_DIR/../install/setup.bash && ros2 launch sensor_tools open_multi_gripper.launch.py l_depth_camera_no:=_$l_depth_camera_no r_depth_camera_no:=_$r_depth_camera_no l_serial_port:=$l_serial_port r_serial_port:=$r_serial_port l_fisheye_port:=$l_fisheye_port r_fisheye_port:=$r_fisheye_port camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps
fi
"""
    elif select == "3":
        path = "start_sensor_gripper.bash"
        content = f"""
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
camera_fps=30
camera_width=640
camera_height=480
sensor_depth_camera_no={left_info[0]}
gripper_depth_camera_no={right_info[0]}

sensor_serial_port=/dev/ttyUSB50
gripper_serial_port=/dev/ttyUSB60
sudo chmod a+rw /dev/ttyUSB*
sensor_fisheye_port=50
gripper_fisheye_port=60
sudo chmod a+rw /dev/video*

source /opt/ros/humble/setup.bash && cd $SCRIPT_DIR/../install/sensor_tools/share/sensor_tools/scripts/ && chmod 777 usb_camera.py
source $SCRIPT_DIR/../install/setup.bash && ros2 launch sensor_tools open_sensor_gripper.launch.py sensor_depth_camera_no:=_$sensor_depth_camera_no gripper_depth_camera_no:=_$gripper_depth_camera_no sensor_serial_port:=$sensor_serial_port gripper_serial_port:=$gripper_serial_port sensor_fisheye_port:=$sensor_fisheye_port gripper_fisheye_port:=$gripper_fisheye_port camera_fps:=$camera_fps camera_width:=$camera_width camera_height:=$camera_height camera_profile:=$camera_width,$camera_height,$camera_fps
"""
    else:
        path = "start_sensor_2grippers_global_camera.bash"
        content = f"""#!/usr/bin/env bash
bash "{os.path.join(START_PIKA_DIR, 'start_single_arm_teleop_capture_sensor_2grippers.sh')}"
"""

    write_executable(path, content)
    return path


def generate_start_pika_device_config(sensor_info, gripper_a_info, gripper_b_info):
    content = f"""#!/usr/bin/env bash

# 由 scripts/setup_device.py 自动生成
# 场景: 1 sensor + 2 grippers，其中 gripper_B 仅作为 global_camera 数据源

SENSOR_SERIAL_PORT="/dev/ttyUSB50"
GRIPPER_A_SERIAL_PORT="/dev/ttyUSB60"
GRIPPER_B_SERIAL_PORT="/dev/ttyUSB61"

SENSOR_FISHEYE_PORT="50"
GRIPPER_A_FISHEYE_PORT="60"
GRIPPER_B_FISHEYE_PORT="61"

SENSOR_DEPTH_CAMERA_NO="{sensor_info[0]}"
GRIPPER_A_DEPTH_CAMERA_NO="{gripper_a_info[0]}"
GRIPPER_B_GLOBAL_CAMERA_SERIAL_NO="{gripper_b_info[0]}"
"""
    write_executable(START_PIKA_DEVICE_CONFIG, content)
    return START_PIKA_DEVICE_CONFIG


def prompt_and_get_device_info(label):
    print(f"请插入{label}设备，然后按回车键继续...")
    input()
    print(f"正在获取{label}设备信息...")
    while True:
        info = get_device_info()
        if not info[0]:
            print(f"无法获取{label}设备信息，请检查设备连接，然后按回车键继续...")
            input()
        else:
            break
    print(f"{label}设备信息: {info[0]} {info[1]} {info[2]}")
    return info


def verify_binding(select):
    while True:
        print("请拔插设备，注意插入先前绑定的同一个USB口。然后按回车键检查是否绑定成功...")
        input()
        print("请等待...")
        time.sleep(5)
        video_list = run_command("ls /dev | grep video")
        usb_list = run_command("ls /dev | grep ttyUSB")
        if (select == "1" or select == "3" or select == "4") and video_list.find("50") < 0:
            print("找不到sensor鱼眼")
            continue
        if select == "1" and video_list.find("51") < 0:
            print("找不到第二个sensor鱼眼")
            continue
        if (select == "2" or select == "3" or select == "4") and video_list.find("60") < 0:
            print("找不到gripper_A鱼眼")
            continue
        if (select == "2" or select == "4") and video_list.find("61") < 0:
            print("找不到gripper_B鱼眼")
            continue
        if (select == "1" or select == "3" or select == "4") and usb_list.find("50") < 0:
            print("找不到sensor串口")
            continue
        if select == "1" and usb_list.find("51") < 0:
            print("找不到第二个sensor串口")
            continue
        if (select == "2" or select == "3" or select == "4") and usb_list.find("60") < 0:
            print("找不到gripper_A串口")
            continue
        if (select == "2" or select == "4") and usb_list.find("61") < 0:
            print("找不到gripper_B串口")
            continue
        break


def main():
    print("=== pika配置工具 ===")
    while True:
        select = input(
            "请选择绑定\n"
            "1.两个pika sensor(手持夹爪)\n"
            "2.两个pika gripper(安装于机械臂上的夹爪)\n"
            "3.一个pika sensor 一个pika gripper\n"
            "4.一个pika sensor + 两个pika gripper（第二个gripper作为global_camera）\n"
            "请输入："
        )
        if select in ("1", "2", "3", "4"):
            break
        print("请输入1、2、3或4")

    if select == "1":
        first_label, second_label, third_label = "左sensor", "右sensor", None
    elif select == "2":
        first_label, second_label, third_label = "左gripper", "右gripper", None
    elif select == "3":
        first_label, second_label, third_label = "sensor", "gripper", None
    else:
        first_label, second_label, third_label = "sensor", "gripper_A（teleop）", "gripper_B（global_camera）"

    first_info = prompt_and_get_device_info(first_label)

    print(f"请拔出{first_label}设备，插入{second_label}设备（注意不要插在同一个USB口，配置完成后USB口不能改变），然后按回车键继续...")
    input()
    second_info = prompt_and_get_device_info(second_label)

    third_info = None
    if third_label is not None:
        print(f"请拔出{second_label}设备，插入{third_label}设备（注意不要插在同一个USB口，配置完成后USB口不能改变），然后按回车键继续...")
        input()
        third_info = prompt_and_get_device_info(third_label)

    print("正在生成配置文件...")
    setup_path = generate_setup_bash(first_info, second_info, select, third_info)
    start_path = generate_start_bash(first_info, second_info, select)

    generated_files = [setup_path, start_path]
    if select == "4":
        generated_files.append(generate_start_pika_device_config(first_info, second_info, third_info))

    print("配置完成！已生成以下文件：")
    for index, path in enumerate(generated_files, start=1):
        print(f"{index}. {path}")

    print(f"执行{setup_path}")
    run_command(f"bash {setup_path}")
    print("执行完成。")

    verify_binding(select)

    print("绑定成功，启动设备方法：")
    print(f"然后运行: bash {start_path}")


if __name__ == "__main__":
    main()
