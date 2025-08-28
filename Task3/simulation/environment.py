from robot.robot_env import UR5Robotiq85
import pybullet as p
import pybullet_data
import math

class Environment:
    def __init_data_get__(self):
        self.robot_id = {}
        self.basket = {}
        self.objects = {}

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)

        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)
        p.loadURDF("table/table.urdf", [0.5, 0, 0],globalScaling=1.2)

        robot_id_1 = UR5Robotiq85([-0.35, 0.0, 0.8], [0, 0, 0])
        robot_id_2 = UR5Robotiq85([1.35, 0.0, 0.8], [0, 0, math.pi])
        robot_id_1.load()
        robot_id_2.load()

        sponge = p.loadURDF("my_objects/026_sponge/google_16k/026_sponge.urdf", [0.12, 0.0, 0.8], globalScaling=1.2)

        base_orientation = p.getQuaternionFromEuler([0, 0, -(math.pi / 2)])
        drawer = p.loadURDF("my_objects/drawer/urdf/drawer.urdf", [0.4, 0.5, 0.8], base_orientation ,globalScaling=0.4,useFixedBase=True)

        self.robot_id = {
            "robot": robot_id_1,
            "human": robot_id_2,
        }

        self.objects = {
            "sponge": sponge,
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

