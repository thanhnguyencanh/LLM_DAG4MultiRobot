import math
import pybullet as p
import pybullet_data
from simulation.objects_simu import create_basket, create_item

class Environment:
    def __init__(self):
        self.robot_id = {}
        self.basket = {}
        self.objects = {}

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)
        p.loadURDF("table/table.urdf", [0.5, 0, 0])

        robot_id_1 = p.loadURDF("franka_panda/panda.urdf", [-0.35, 0.0, 0.62], useFixedBase=True)
        rotation_quat = p.getQuaternionFromEuler([0, 0, 3.14159])
        robot_id_2 = p.loadURDF("franka_panda/panda.urdf", [1.35, 0.0, 0.62], rotation_quat, useFixedBase=True)

        apple = create_item([1.005, -0.3, 0.65], 'box', [0.025, 0.025, 0.02], [1, 0, 0, 1])
        teddy_bear = create_item([0.76, 0.0, 0.65], 'box', [0.025, 0.025, 0.02], [0.25, 0.25, 0, 1])

        cake = create_item([0.32, -0.2, 0.65], 'box', [0.025, 0.025, 0.025], [1, 1, 0, 1])
        toy_car = create_item([0.3, 0.1, 0.65], 'box', [0.025, 0.025, 0.025], [0, 0, 1, 1])

        basket1_ids, basket1_center = create_basket([1.005, 0.35, 0.6])
        basket2_ids, basket2_center = create_basket([0.3, 0.35, 0.6])

        self.robot_id = {
            "robot": robot_id_1,
            "human": robot_id_2,
        }

        self.objects = {
            "cake": cake,
            "apple": apple,
            "teddy_bear": teddy_bear,
            "toy_car": toy_car,
        }

        self.basket = {
            "box1": {"ids": basket1_ids, "center": basket1_center},
            "box2": {"ids": basket2_ids, "center": basket2_center},
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

