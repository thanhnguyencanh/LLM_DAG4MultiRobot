import pybullet as p
import pybullet_data
from robot.robot_env import UR5Robotiq85
import math
def print_robot_info(robot_id, name):
    print(f"\n===== {name} =====")
    num_joints = p.getNumJoints(robot_id)
    print(f"Số khớp: {num_joints}")

    for j in range(num_joints):
        joint_info = p.getJointInfo(robot_id, j)
        joint_name = joint_info[1].decode("utf-8")
        joint_type = joint_info[2]
        lower_limit = joint_info[8]
        upper_limit = joint_info[9]
        max_force = joint_info[10]
        max_velocity = joint_info[11]
        parent_idx = joint_info[16]
        link_name = joint_info[12].decode("utf-8")

        print(f"Joint {j} | name: {joint_name} | link: {link_name} | "
              f"type: {joint_type} | parent: {parent_idx} | "
              f"limit: [{lower_limit}, {upper_limit}] | "
              f"max_force: {max_force} | max_vel: {max_velocity}")

    # lấy vị trí và orientation gốc
    pos, orn = p.getBasePositionAndOrientation(robot_id)
    print(f"Base position: {pos}, orientation: {orn}")

def main():
    p.connect(p.GUI)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())

    # load hai robot giống nhau nhưng khác vị trí
    robot_id_1 = UR5Robotiq85([-0.35, 0.0, 0.8], [0, 0, 0])
    robot_id_2 = UR5Robotiq85([1.35, 0.0, 0.8], [0, 0, math.pi])
    robot_id_1.load()
    robot_id_2.load()

    print_robot_info(robot_id_1.id, "Robot1")
    print_robot_info(robot_id_2.id, "Robot2")

if __name__ == "__main__":
    main()
