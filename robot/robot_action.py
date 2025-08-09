import pybullet as p
import time
import math

end_effector_index = 11

def get_position(obj_id):
    pos, _ = p.getBasePositionAndOrientation(obj_id)
    adjusted_pos = (pos[0], pos[1], pos[2] + 0.01)
    return adjusted_pos

def wait_simulation(steps=100):
    for _ in range(steps):
        p.stepSimulation()
        time.sleep(1. / 240.)

def move_to_target(robot_id, target_pos, steps=50):
    current_joint_states = [p.getJointState(robot_id, i)[0] for i in range(7)]

    target_joint_poses = p.calculateInverseKinematics(
        bodyUniqueId=robot_id,
        endEffectorLinkIndex=end_effector_index,
        targetPosition=target_pos,
    )
    target_joint_angles = target_joint_poses[:7]
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
    try:

        p.setJointMotorControl2(robot_id, 9, p.POSITION_CONTROL,
                                targetPosition=0.04, force=50)
        p.setJointMotorControl2(robot_id, 10, p.POSITION_CONTROL,
                                targetPosition=0.04, force=50)
        wait_simulation()


        approach_pos = list(target_pos)
        approach_pos[2] += 0.3
        move_to_target(robot_id, approach_pos)
        wait_simulation()

        move_to_target(robot_id, target_pos)
        wait_simulation()


        p.setJointMotorControl2(robot_id, 9, p.POSITION_CONTROL,
                                targetPosition=0.0, force=50)
        p.setJointMotorControl2(robot_id, 10, p.POSITION_CONTROL,
                                targetPosition=0.0, force=50)
        wait_simulation()


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

        lift_pos = list(target_pos)
        lift_pos[2] += 0.5
        move_to_target(robot_id, lift_pos)
        wait_simulation()

        return constraint_id

    except Exception as e:
        print(f"Error during pick operation: {e}")
        return None

def place(robot_name, target_pos, constraint_id, robot_id_dict):
    robot_home_pos = [-0.1, 0.0, 2.0]
    human_home_pos = [1.0, 0.0, 2.0]

    if robot_name not in robot_id_dict:
        print(f"[WARN] robot_name '{robot_name}' không hợp lệ")
        return

    robot_pybullet_id = robot_id_dict[robot_name]

    above_pos = list(target_pos)
    above_pos[2] += 0.2
    move_to_target(robot_pybullet_id, above_pos)
    wait_simulation()

    move_to_target(robot_pybullet_id, target_pos)
    wait_simulation()

    p.setJointMotorControl2(robot_pybullet_id, 9, p.POSITION_CONTROL,
                            targetPosition=0.04, force=50)
    p.setJointMotorControl2(robot_pybullet_id, 10, p.POSITION_CONTROL,
                            targetPosition=0.04, force=50)
    wait_simulation()

    if constraint_id is not None:
        p.removeConstraint(constraint_id)


    if robot_name == 'human':
        move_to_target(robot_pybullet_id, human_home_pos)
        wait_simulation()
    elif robot_name == 'robot':
        move_to_target(robot_pybullet_id, robot_home_pos)
        wait_simulation()
    else:
        print(f"[WARN] Không có vị trí home cho robot_name={robot_name}")
