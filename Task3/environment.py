from robot.robot_env import UR5Robotiq85
import pybullet as p
import pybullet_data
import math
from paths import (
    PLATE_URDF, BANANA_URDF, APPLE_URDF, SPOON_URDF,
     DRAWER_URDF, ORANGE_CUP_URDF, PURPLE_CUP_URDF
)

class Environment:
    def __init__(self):
        self.robot_id = {}
        self.basket = {}
        self.objects = {
            "plate": (0.9, -0.25, 0.8),
            "banana": (0.9, 0.2, 0.8),
            "apple": (0.15, 0.36, 0.8),
            "spoon": (0.3, 0.2, 0.8),
            "drawer": (0.25, -0.65, 0.7),
            "orange_cup": (1.0, 0.38, 0.8),
            "purple_cup": (0.3, -0.27, 0.8),
        }

    def get_object_names(self):
        return list(self.objects.keys())

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)
        p.loadURDF("table/table.urdf", [0.5, 0, 0],globalScaling=1.2)

        robot_id_2  = UR5Robotiq85([-0.35, 0.0, 0.8], [0, 0, 0])
        robot_id_2.load()
        robot_id_1 = UR5Robotiq85([1.35, 0.0, 0.8], [0, 0, math.pi])
        robot_id_1.load()


        plate = p.loadURDF(PLATE_URDF, [0.8, -0.1, 0.8], globalScaling=1.15)
        banana = p.loadURDF(BANANA_URDF, [0.9, 0.2, 0.8], globalScaling=1.0)
        apple = p.loadURDF(APPLE_URDF, [0.15, 0.36, 0.8], globalScaling=0.1)
        spoon = p.loadURDF(SPOON_URDF, [0.3, 0.2, 0.8], globalScaling=1.0)

        base_orientation = p.getQuaternionFromEuler([0, 0, -(math.pi / 2)])
        drawer = p.loadURDF(DRAWER_URDF, [0.25, -0.65, 0.7], base_orientation, globalScaling=0.4, useFixedBase=True)

        orange_cup = p.loadURDF(ORANGE_CUP_URDF, [1.0, 0.38, 0.8], globalScaling=1.0)
        purple_cup = p.loadURDF(PURPLE_CUP_URDF, [0.3, -0.1, 0.8], globalScaling=1.0)

        self.robot_id = {
            "robot1": robot_id_1,
            "robot2": robot_id_2,
        }

        self.objects = {
            "banana": banana,
            "apple": apple,
            "spoon": spoon,
            "plate": plate,
            "orange_cup": orange_cup,
            "purple_cup": purple_cup,
            "drawer": drawer,
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

