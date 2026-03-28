cd /mnt/nas/projects/pika_ros/install/libsurvive/bin && ./survive-cli --force-calibrate
cd /mnt/nas/projects/pika_ros/install/libsurvive/bin && ./survive-cli

conda deactivate
source /mnt/nas/projects/pika_ros/install/setup.bash
cd /mnt/nas/projects/pika_ros/scripts && bash start_sensor_gripper.bash

source /mnt/nas/projects/pika_ros/install/setup.bash
conda activate pika
ros2 launch pika_remote_diana teleop_right_diana.launch.py 

source /mnt/nas/projects/pika_ros/install/setup.bash
ros2 launch data_tools run_data_capture.launch.py useService:=true type:=multi_pika_teleop datasetDir:=/mnt/nas/datasets/teleop_diana episodeIndex:=0  # 双夹持器遥操作

ros2 launch data_tools run_data_sync.launch.py type:=multi_pika_teleop datasetDir:=/mnt/nas/datasets/teleop_diana episodeIndex:=-1

cd /mnt/nas/projects/pika_ros/scripts
python3 data_to_hdf5.py --type multi_pika_teleop --datasetDir /mnt/nas/datasets/teleop_diana --useCameraPointCloud ""  # 双夹持器遥操作

python3 data_to_hdf5.py --type multi_pika_teleop --datasetDir $HOME/agilex/data/ --useCameraPointCloud ""  # 双夹持器遥操作