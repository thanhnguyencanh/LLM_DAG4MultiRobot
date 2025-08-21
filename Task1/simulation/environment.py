import pybullet as p
import pybullet_data
from my_objects.objects_simu import create_item


class Environment:
    def __init__(self):
        self.robot_id = {}
        self.basket = {}
        self.objects = {}

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)
        p.loadURDF("table/table.urdf", [0.5, 0, 0],globalScaling=1.2)

        robot_id_1 = p.loadURDF("franka_panda/panda.urdf", [-0.35, 0.0, 0.8], useFixedBase=True)
        rotation_quat = p.getQuaternionFromEuler([0, 0, 3.14159])
        robot_id_2 = p.loadURDF("franka_panda/panda.urdf", [1.35, 0.0, 0.8], rotation_quat, useFixedBase=True)

        green_bowl = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/bowl_green/bowl_green.urdf", [0.9, 0.37, 0.8], globalScaling=0.1)

        red_bowl = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/bowl_red/google_16k/bowl_red.urdf", [0.3, -0.33, 0.8], globalScaling=0.1)

        yellow_bowl = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/bowl_yellow/google_16k/bowl_yellow.urdf", [0.3, 0.33, 0.8], globalScaling=0.1)

        red_cube = create_item([1.005, -0.3, 0.8], 'box', [0.025, 0.025, 0.02], [1, 0, 0, 1])
        yellow_cube = create_item([0.22, -0.1, 0.8], 'box', [0.025, 0.025, 0.02], [1, 1, 0, 1])

        green_cube_1 = create_item([0.32, 0.1, 0.8], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])
        green_cube_2 = create_item([0.8, 0.0, 0.8], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])

        self.robot_id = {
            "robot": robot_id_1,
            "human": robot_id_2,
        }

        self.objects = {
           "red_cube": red_cube,
            "yellow_cube": yellow_cube,
            "green_cube_1": green_cube_1,
            "green_cube_2": green_cube_2,
            "green_bowl": green_bowl,
            "yellow_bowl": yellow_bowl,
            "red_bowl": red_bowl,
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

