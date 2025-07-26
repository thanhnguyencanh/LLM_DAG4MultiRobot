import pybullet as p
import time
import  math
def get_object_position(obj_id):
    pos, _ = p.getBasePositionAndOrientation(obj_id)
    adjusted_pos = (pos[0], pos[1], pos[2] + 0.2)
    return adjusted_pos

def move_to_target(robot_id, target_pos, steps=100):
    end_effector_index = 11  # Chỉ số của gripper trên Panda

    # Gán góc Euler để end effector hướng từ trên xuống
    roll = math.pi
    pitch = 0
    yaw = math.pi / 2
    euler_angles = [roll, pitch, yaw]
    orientation = p.getQuaternionFromEuler(euler_angles)

    # Lấy góc khớp hiện tại của 7 khớp chính
    current_joint_states = [p.getJointState(robot_id, i)[0] for i in range(7)]

    # Giải IK để lấy joint angles cho target position + orientation
    target_joint_poses = p.calculateInverseKinematics(
        bodyUniqueId=robot_id,
        endEffectorLinkIndex=end_effector_index,
        targetPosition=target_pos,
        targetOrientation=orientation
    )

    # Chỉ lấy 7 khớp đầu ra (Panda có 7 khớp chính)
    target_joint_angles = target_joint_poses[:7]

    # Di chuyển nội suy mượt từ vị trí hiện tại đến vị trí mục tiêu
    for step in range(steps):
        interpolated_pose = [
            current + (target - current) * (step + 1) / steps
            for current, target in zip(current_joint_states, target_joint_angles)
        ]

        for i in range(7):
            p.setJointMotorControl2(
                bodyUniqueId=robot_id,
                jointIndex=i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=interpolated_pose[i],
                force=5 * 240.0
            )

        p.stepSimulation()
        time.sleep(1. / 240.)


def pick(robot_id, object_id, target_pos):
    end_effector_index = 11

    # 1. Di chuyển đến trên cao
    approach_pos = list(target_pos)
    approach_pos[2] += 0.3
    move_to_target(robot_id, approach_pos)
    for _ in range(100): p.stepSimulation(); time.sleep(1./240.)

    # 2. Hạ xuống

    move_to_target(robot_id, target_pos)
    for _ in range(100): p.stepSimulation(); time.sleep(1./240.)

    # 3. Kẹp gripper
    p.setJointMotorControl2(robot_id, 9, p.POSITION_CONTROL, targetPosition=0.0, force=50)
    p.setJointMotorControl2(robot_id, 10, p.POSITION_CONTROL, targetPosition=0.0, force=50)
    for _ in range(100): p.stepSimulation(); time.sleep(1./240.)

    # 4. Tạo constraint giữa gripper và vật
    constraint_id = p.createConstraint(
        parentBodyUniqueId=robot_id,
        parentLinkIndex=end_effector_index,
        childBodyUniqueId=object_id,
        childLinkIndex=-1,
        jointType=p.JOINT_FIXED,
        jointAxis=[0, 0, 0],
        parentFramePosition=[0, 0, 0],
        childFramePosition=[0, 0, 0]
    )

    # 5. Nhấc lên
    lift_pos = list(target_pos)
    lift_pos[2] += 0.5
    move_to_target(robot_id, lift_pos)
    for _ in range(100): p.stepSimulation(); time.sleep(1./240.)


    fi_pos = [0.4, 0.3, 0.6]
    fi_pos[2] += 0.5
    move_to_target(robot_id,fi_pos)
    for _ in range(100): p.stepSimulation(); time.sleep(1. / 240.)

    final_pos = list(fi_pos)
    final_pos[2] -= 0.25
    move_to_target(robot_id, final_pos)
    for _ in range(100): p.stepSimulation(); time.sleep(1. / 240.)
    p.removeConstraint(constraint_id)

    return constraint_id



