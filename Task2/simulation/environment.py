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

        plate = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/029_plate/google_16k/029_plate.urdf", [0.8, -0.25, 0.8], globalScaling=1.2)
        banana = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/011_banana/google_16k/011_banana.urdf", [1.0, 0.0, 0.8], globalScaling=1.0)

        apple = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/013_apple/google_16k/013_apple.urdf", [0.15, 0.36, 0.8], globalScaling=0.1)
        spoon = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/031_spoon/google_16k/031_spoon.urdf", [0.3, 0.2, 0.8], globalScaling=1.0)

        sponge = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/026_sponge/google_16k/026_sponge.urdf", [0.12, 0.0, 0.8], globalScaling=1.2)
        drawer = create_item([0.12, -1.2, 0.3], 'box', [0.25, 0.25, 0.25], [1, 1, 1, 1])

        orange_cup = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/065-a_cups/google_16k/065-a_cups.urdf", [1.0, 0.33, 0.8], globalScaling=1.0)
        purple_cup = p.loadURDF("D:/track/Human_Robot_Colab/my_objects/065-f_cups/google_16k/065-f_cups.urdf", [0.3, -0.27, 0.8], globalScaling=1.0)
        self.robot_id = {
            "robot": robot_id_1,
            "human": robot_id_2,
        }

        self.objects = {
            "banana" : banana,
            "apple" : apple,
            "spoon" :spoon,
            "sponge" :sponge,
            "plate": plate,
            "orange_cup":  orange_cup,
            "purple_cup" :  purple_cup,
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

