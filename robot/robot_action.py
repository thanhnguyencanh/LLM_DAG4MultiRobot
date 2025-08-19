import pybullet as p
import time
import numpy as np

END_EFFECTOR_INDEX = 11
GRIPPER_OPEN = 0.04
GRIPPER_CLOSED = 0.0
SIMULATION_STEPS = 150
MOVE_STEPS = 100
GRIPPER_STEPS = 30
FORCE = 50
MAX_VELOCITY = 2.0
HOME_POSITIONS = {
    'robot': [-0.1, 0.0, 2.0],
    'human': [1.0, 0.0, 2.0]
}


def get_position(obj_id):
    pos, _ = p.getBasePositionAndOrientation(obj_id)
    return (pos[0], pos[1], pos[2] + 0.01)


def wait_simulation(steps=SIMULATION_STEPS):
    for _ in range(steps):
        p.stepSimulation()
        time.sleep(1 / 240.0)


def set_gripper(robot_id, target_position, steps=GRIPPER_STEPS):
    current_pos = [p.getJointState(robot_id, joint)[0] for joint in [9, 10]]
    for step in range(steps):
        progress = smooth_step(step / steps)
        interpolated_pos = current_pos[0] + (target_position - current_pos[0]) * progress
        for joint in [9, 10]:
            p.setJointMotorControl2(robot_id, joint, p.POSITION_CONTROL,
                                    targetPosition=interpolated_pos,
                                    force=FORCE,
                                    maxVelocity=0.5)
        p.stepSimulation()
        time.sleep(1 / 240.0)

def smooth_step(t):
    return t * t * (3.0 - 2.0 * t)

def bezier_curve(t, p0, p1, p2, p3):
    return ((1 - t) ** 3 * np.array(p0) +
            3 * (1 - t) ** 2 * t * np.array(p1) +
            3 * (1 - t) * t ** 2 * np.array(p2) +
            t ** 3 * np.array(p3))


def move_to_target(robot_id, target_pos, steps=MOVE_STEPS, use_smooth_trajectory=True):
    current_joints = [p.getJointState(robot_id, i)[0] for i in range(7)]
    current_ee_pos = p.getLinkState(robot_id, END_EFFECTOR_INDEX)[0]
    target_joints = p.calculateInverseKinematics(
        bodyUniqueId=robot_id,
        endEffectorLinkIndex=END_EFFECTOR_INDEX,
        targetPosition=target_pos
    )[:7]

    if use_smooth_trajectory and np.linalg.norm(np.array(target_pos) - np.array(current_ee_pos)) > 0.1:
        control1 = np.array(current_ee_pos) + np.array([0, 0, 0.1])
        control2 = np.array(target_pos) + np.array([0, 0, 0.1])
        trajectory_points = []
        for i in range(steps):
            t = i / (steps - 1)
            smooth_t = smooth_step(t)
            point = bezier_curve(smooth_t, current_ee_pos, control1, control2, target_pos)
            trajectory_points.append(point)
        for point in trajectory_points:
            joints = p.calculateInverseKinematics(
                bodyUniqueId=robot_id,
                endEffectorLinkIndex=END_EFFECTOR_INDEX,
                targetPosition=point
            )[:7]
            for i, angle in enumerate(joints):
                p.setJointMotorControl2(robot_id, i, p.POSITION_CONTROL,
                                        targetPosition=angle,
                                        force=5 * 240.0,
                                        maxVelocity=MAX_VELOCITY)
            p.stepSimulation()
            time.sleep(1 / 240.0)
    else:
        for step in range(steps):
            progress = smooth_step(step / steps)
            interpolated = [
                current + (target - current) * progress
                for current, target in zip(current_joints, target_joints)
            ]
            for i, angle in enumerate(interpolated):
                p.setJointMotorControl2(robot_id, i, p.POSITION_CONTROL,
                                        targetPosition=angle,
                                        force=5 * 240.0,
                                        maxVelocity=MAX_VELOCITY)
            p.stepSimulation()
            time.sleep(1 / 240.0)


def pick(robot_id, object_id, target_pos):
    try:
        set_gripper(robot_id, GRIPPER_OPEN)
        approach_pos = list(target_pos)
        approach_pos[2] += 0.3
        move_to_target(robot_id, approach_pos, use_smooth_trajectory=True)
        move_to_target(robot_id, target_pos, steps=60, use_smooth_trajectory=False)
        set_gripper(robot_id, GRIPPER_CLOSED, steps=40)
        time.sleep(0.5)
        constraint_id = p.createConstraint(
            parentBodyUniqueId=robot_id,
            parentLinkIndex=END_EFFECTOR_INDEX,
            childBodyUniqueId=object_id,
            childLinkIndex=-1,
            jointType=p.JOINT_FIXED,
            jointAxis=[0, 0, 0],
            parentFramePosition=[0, 0, 0],
            childFramePosition=[0, 0, 0]
        )
        lift_pos = list(target_pos)
        lift_pos[2] += 0.5
        move_to_target(robot_id, lift_pos, steps=80, use_smooth_trajectory=True)
        wait_simulation(50)
        return constraint_id
    except Exception as e:
        print(f"Pick error: {e}")
        return None


def place(agent_name, target_pos, constraint_id, robot_ids):
    if agent_name not in robot_ids:
        print(f"Unknown agent: {agent_name}")
        return
    robot_id = robot_ids[agent_name]
    above_pos = list(target_pos)
    above_pos[2] += 0.3
    move_to_target(robot_id, above_pos, use_smooth_trajectory=True)
    move_to_target(robot_id, target_pos, steps=60, use_smooth_trajectory=False)
    time.sleep(0.2)
    set_gripper(robot_id, GRIPPER_OPEN, steps=50)
    time.sleep(0.3)
    if constraint_id:
        p.removeConstraint(constraint_id)
    retreat_pos = list(target_pos)
    retreat_pos[2] += 0.2
    move_to_target(robot_id, retreat_pos, steps=40, use_smooth_trajectory=False)
    if agent_name in HOME_POSITIONS:
        move_to_target(robot_id, HOME_POSITIONS[agent_name], use_smooth_trajectory=True)
        wait_simulation(30)


def sweep(robot_id, obj_id, sweep_distance=0.2, sweep_count=3):
    target_pos = get_position(obj_id)
    constraint_id = pick(robot_id, obj_id, target_pos)
    if not constraint_id:
        return
    wait_simulation()
    start_pos = list(target_pos)
    end_pos = list(target_pos)
    end_pos[1] += sweep_distance
    for _ in range(sweep_count):
        move_to_target(robot_id, end_pos)
        wait_simulation()
        move_to_target(robot_id, start_pos)
        wait_simulation()
    set_gripper(robot_id, GRIPPER_OPEN)
    if constraint_id:
        p.removeConstraint(constraint_id)
