"""
Robot Action Module
Contains primitive actions for robot manipulation: pick, place, move, sweep.
"""

import pybullet as p
import time

# ============ CONFIGURATION CONSTANTS ============
SIMULATION_STEPS = 50       # Default simulation steps per action
GRIPPER_OPEN = 0.1          # Gripper open position (meters)
GRIPPER_CLOSE = 0.0         # Gripper closed position
APPROACH_HEIGHT = 0.3       # Height above object for approach
GRASP_HEIGHT = 0.12         # Height for grasping object
PLACE_HEIGHT = 0.15         # Height for placing object
DEFAULT_SLEEP = 0.01        # Sleep time between simulation steps


def get_position(obj_id):
    """Get current [x, y, z] position of an object."""
    pos, _ = p.getBasePositionAndOrientation(obj_id)
    return (pos[0], pos[1], pos[2])


def wait_simulation(steps=SIMULATION_STEPS, sleep_time=DEFAULT_SLEEP):
    """Step the simulation forward and wait."""
    for _ in range(steps):
        p.stepSimulation()
        time.sleep(sleep_time)


def move_to_target(robot_id, target_pos, target_orn):
    if target_orn is None:
        eef_state = p.getLinkState(robot_id.id, robot_id.eef_id)
        target_orn = eef_state[1]

    robot_id.move_arm_ik(target_pos, target_orn)
    time.sleep(0.5)
    wait_simulation(50)


def set_gripper(robot_id, open_length):
    open_length = max(robot_id.gripper_range[0],
                      min(open_length, robot_id.gripper_range[1]))
    robot_id.move_gripper(open_length)
    wait_simulation(steps=20)
    return True


def pick(robot_id, object_id, target_pos=None):
    """
    Pick up an object at target position.
    
    Sequence: Home pose -> Approach -> Grasp -> Close gripper -> Lift
    
    Args:
        robot_id: Robot instance
        object_id: PyBullet object ID to pick
        target_pos: [x, y, z] position of object
    
    Returns:
        constraint_id: PyBullet constraint ID (for attaching object to gripper)
    """
    # Move to home position first
    target_joint_positions = [0, -1.57, 1.57, -1.5, -1.57, 0.0]
    for i, joint_id in enumerate(robot_id.arm_controllable_joints):
        p.setJointMotorControl2(robot_id.id, joint_id, p.POSITION_CONTROL, target_joint_positions[i])
    wait_simulation(steps=200)

    # Get current end-effector orientation
    eef_state = p.getLinkState(robot_id.id, robot_id.eef_id)
    eef_orientation = eef_state[1]

    # Step 1: Move to approach position (above object)
    approach_pos = [target_pos[0], target_pos[1], target_pos[2] + APPROACH_HEIGHT]
    robot_id.move_arm_ik(approach_pos, eef_orientation)
    wait_simulation(50)

    # Step 2: Lower to grasp position
    grasp_pos = [target_pos[0], target_pos[1], target_pos[2] + GRASP_HEIGHT]
    robot_id.move_arm_ik(grasp_pos, eef_orientation)
    wait_simulation(50)

    # Step 3: Close gripper
    set_gripper(robot_id, GRIPPER_CLOSE)

    # Step 4: Create fixed constraint to attach object to gripper
    try:
        constraint_id = p.createConstraint(
            parentBodyUniqueId=robot_id.id,
            parentLinkIndex=robot_id.eef_id,
            childBodyUniqueId=object_id,
            childLinkIndex=-1,
            jointType=p.JOINT_FIXED,
            jointAxis=[0, 0, 0],
            parentFramePosition=[0.15, 0.0, -0.005],
            childFramePosition=[0, 0, 0]
        )
        print(f"Constraint created: {constraint_id}")
    except Exception as e:
        print(f"Failed to create constraint: {e}")
        constraint_id = None

    # Step 5: Lift object
    robot_id.move_arm_ik([target_pos[0], target_pos[1], target_pos[2] + 0.4], eef_orientation)
    wait_simulation(50)

    return constraint_id


def place(agent_name, target_pos, constraint_id, robot_ids):
    """
    Place an object at target position.
    
    Sequence: Move above target -> Lower -> Open gripper -> Release -> Lift -> Home
    
    Args:
        agent_name: Name of the robot agent (e.g., "robot1")
        target_pos: [x, y, z] position to place object
        constraint_id: PyBullet constraint ID from pick action
        robot_ids: Dict mapping agent names to robot instances
    """
    if constraint_id is None:
        print("No constraint found. Cannot place object.")
        return
    robot_id = robot_ids[agent_name]

    eef_state = p.getLinkState(robot_id.id, robot_id.eef_id)
    eef_orientation = eef_state[1]

    # Step 1: Move above target position
    robot_id.move_arm_ik([target_pos[0], target_pos[1], target_pos[2] + 0.3], eef_orientation)
    wait_simulation(50)

    # Step 2: Lower toward target
    robot_id.move_arm_ik([target_pos[0], target_pos[1], target_pos[2] + 0.2], eef_orientation)
    wait_simulation(50)

    # Step 3: Open gripper to release object
    robot_id.move_gripper(GRIPPER_OPEN)
    wait_simulation(20)

    # Step 4: Remove constraint to detach object from gripper
    if constraint_id:
        p.removeConstraint(constraint_id)

    # Step 5: Lift arm and return to home position
    robot_id.move_arm_ik([target_pos[0], target_pos[1], target_pos[2] + 0.3], eef_orientation)
    wait_simulation(50)

    move_to_home(robot_id)
    wait_simulation(50)


def sweep(robot_id, obj_id, sweep_count=2, z_height=0.15, sweep_distance=0.3):
    target_pos = get_position(obj_id)
    downward_orientation = p.getQuaternionFromEuler([0, 1.57, 0])
    set_gripper(robot_id, GRIPPER_OPEN)
    approach_pos = [target_pos[0], target_pos[1], target_pos[2] + APPROACH_HEIGHT]
    move_to_target(robot_id, approach_pos, downward_orientation)

    grasp_pos = [target_pos[0], target_pos[1], target_pos[2] + GRASP_HEIGHT]
    move_to_target(robot_id, grasp_pos, downward_orientation)

    set_gripper(robot_id, GRIPPER_CLOSE)


    try:
        constraint_id = p.createConstraint(
            parentBodyUniqueId=robot_id.id,
            parentLinkIndex=robot_id.eef_id,
            childBodyUniqueId=obj_id,
            childLinkIndex=-1,
            jointType=p.JOINT_FIXED,
            jointAxis=[0, 0, 0],
            parentFramePosition=[0.15, 0.0, -0.005],
            childFramePosition=[0, 0, 0]
        )
        print(f"Constraint created: {constraint_id}")
    except Exception as e:
        print(f"Failed to create constraint: {e}")
        constraint_id = None
        return

    sweep_pos = [target_pos[0], target_pos[1], z_height + 0.1]
    move_to_target(robot_id, sweep_pos, downward_orientation)

    center_y = target_pos[1]
    pos1 = [target_pos[0], center_y - sweep_distance / 2, z_height]
    pos2 = [target_pos[0], center_y + sweep_distance / 2, z_height]

    for i in range(sweep_count):
        move_to_target(robot_id, pos1, downward_orientation)
        wait_simulation(30)
        move_to_target(robot_id, pos2, downward_orientation)
        wait_simulation(30)


    move_to_target(robot_id, sweep_pos, downward_orientation)
    wait_simulation(30)

    set_gripper(robot_id, GRIPPER_OPEN)
    if constraint_id:
        p.removeConstraint(constraint_id)

    final_pos = [target_pos[0], target_pos[1], target_pos[2] + 0.4]
    move_to_target(robot_id, final_pos, downward_orientation)
    wait_simulation(50)

    move_to_home(robot_id)


def move_to_home(robot_id):
    move_arm_to_joint_positions(robot_id, robot_id.arm_rest_poses)
    set_gripper(robot_id, GRIPPER_OPEN)


def move_arm_to_joint_positions(robot_id, joint_positions):
    for i, joint_id in enumerate(robot_id.arm_controllable_joints):
        p.setJointMotorControl2(
            robot_id.id,
            joint_id,
            p.POSITION_CONTROL,
            joint_positions[i],
            maxVelocity=robot_id.max_velocity
        )
    wait_simulation()