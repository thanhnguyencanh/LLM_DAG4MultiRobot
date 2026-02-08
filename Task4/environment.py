from robot.robot_env import UR5Robotiq85
import pybullet as p
import pybullet_data
import math
from paths import BANANA_URDF, APPLE_URDF, PURPLE_CUP_URDF 
from my_objects.objects_simu import create_hollow_box

# Moved box creation inside setup_simulation to avoid "Not connected" error during import

class Environment:
    def __init__(self):
        self.robot_id = {}
        self.objects = {
            "banana": (0.1, 0.0, 0.9),
            "apple": (0.9, 0.2, 0.9),
            "cup": (0.2, -0.2, 0.9),
            "box1": (0.5, 0.0, 0.75)
        }
        self.handoff_points = {
            "robot1torobot2": [0.55, -0.2, 0.8],
            "robot2torobot1": [0.65, 0.2, 0.8],
        }
        self.agent_positions = {
            "robot1": [1.35, 0.0, 0.8],
            "robot2": [-0.35, 0.0, 0.8],
        }
    def get_object_names(self):
        return list(self.objects.keys())

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)
        p.loadURDF("table/table.urdf", [0.5, 0, 0], globalScaling=1.2)

        robot_id_2 = UR5Robotiq85([-0.35, 0.0, 0.8], [0, 0, 0])
        robot_id_2.load()
        robot_id_1 = UR5Robotiq85([1.35, 0.0, 0.8], [0, 0, math.pi])
        robot_id_1.load()

        banana = p.loadURDF(BANANA_URDF, [0.1, 0.0, 0.9], globalScaling=1.0)
        apple = p.loadURDF(APPLE_URDF, [0.9, 0.2, 0.9], globalScaling=0.13)
        cup = p.loadURDF(PURPLE_CUP_URDF, [0.2, -0.2, 0.9], globalScaling=1.0)

        # Tạo hộp (trả về list gồm 5 ID: [đáy, tường1, tường2, tường3, tường4])
        box_ids = create_hollow_box(
            center_pos=[0.5, 0.0, 0.75],
            width=0.3,
            length=0.3,
            height=0.1,
            thickness=0.02,
            color=[0.6, 0.4, 0.2, 1]
        )

        self.robot_id = {
            "robot1": robot_id_1,
            "robot2": robot_id_2,
        }

        # CẬP NHẬT TẠI ĐÂY:
        # Thay vì gán "box": box_ids, ta chỉ lấy ID của tấm đáy (index 0)
        self.objects = {
            "banana": banana,
            "apple": apple,
            "cup": cup,
            "box": box_ids[0], # Bây giờ "box" là một số nguyên (int), không còn là list
        }


def get_camera_matrices():
    camera_target = [0.6, 0, 0.85]
    camera_pos = [0.6, 0, 1.5]
    camera_up = [0, 1, 0]

    view_matrix = p.computeViewMatrix(
        cameraEyePosition=camera_pos,
        cameraTargetPosition=camera_target,
        cameraUpVector=camera_up
    )

    projection_matrix = p.computeProjectionMatrixFOV(
        fov=60,
        aspect=1.0,
        nearVal=0.01,
        farVal=2.0
    )

    return view_matrix, projection_matrix