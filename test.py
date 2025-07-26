import pybullet as p
import pybullet_data
import time
import math

# Khởi tạo PyBullet
p.connect(p.GUI)
p.setGravity(0, 0, -9.81)
p.setAdditionalSearchPath(pybullet_data.getDataPath())

# Load plane và robot
plane_id = p.loadURDF("plane.urdf")
start_pos = [0, 0, 0]
start_ori = p.getQuaternionFromEuler([0, 0, 0])
robot_id = p.loadURDF("franka_panda/panda.urdf", start_pos, start_ori, useFixedBase=True)

# Lấy index của end-effector
print("=== Danh sách joints ===")
for i in range(p.getNumJoints(robot_id)):
    joint_info = p.getJointInfo(robot_id, i)
    print(f"{i}: {joint_info[1].decode()}")

end_effector_index = 11  # panda_hand_tcp (xác nhận bằng log ở trên)

# Target vị trí và hướng (vị trí dễ với robot)
target_pos = [0.4, -0.2 , 0.0]
target_euler = [math.pi, 0, math.pi/2]  # hướng xuống
target_ori = p.getQuaternionFromEuler(target_euler)

# Tính IK
joint_poses = p.calculateInverseKinematics(robot_id,
                                           end_effector_index,
                                           targetPosition=target_pos,
                                           targetOrientation=target_ori)

# Chỉ lấy 7 khớp chính
joint_poses = joint_poses[:7]

# Gán các góc khớp
for i in range(7):
    p.resetJointState(robot_id, i, joint_poses[i])

# Hiển thị
for _ in range(10000):
    p.stepSimulation()
    time.sleep(1. / 240.)
