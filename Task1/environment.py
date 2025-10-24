from robot.robot_env import UR5Robotiq85
import pybullet as p
import pybullet_data
from my_objects.objects_simu import create_item
import math
from paths import BOWL_GREEN_URDF, BOWL_RED_URDF, BOWL_YELLOW_URDF


class Environment:
    def __init__(self):
        self.robot_id = {}
        self.objects = {
            "green_bowl": (0.9, 0.37, 0.9),
            "red_bowl": (0.3, -0.33, 0.9),
            "yellow_bowl": (0.3, 0.4, 0.9),

            "red_cube": (1.005, -0.3, 0.81),
            "yellow_cube": (0.22, -0.1, 0.8),
            "green_cube_1": (0.32, 0.1, 0.8),
            "green_cube_2": (0.8, 0.0, 0.8),
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
        p.loadURDF("table/table.urdf", [0.5, 0, 0],globalScaling=1.2)

        robot_id_2 = UR5Robotiq85([-0.35, 0.0, 0.8], [0, 0, 0])
        robot_id_2.load()
        robot_id_1 = UR5Robotiq85([1.35, 0.0, 0.8], [0, 0, math.pi])
        robot_id_1.load()

        green_bowl = p.loadURDF(BOWL_GREEN_URDF, [0.9, 0.37, 0.9], globalScaling=0.13)
        red_bowl = p.loadURDF(BOWL_RED_URDF, [0.3, -0.33, 0.9], globalScaling=0.13)
        yellow_bowl = p.loadURDF(BOWL_YELLOW_URDF, [0.3, 0.4, 0.9], globalScaling=0.13)

        red_cube = create_item([1.005, -0.3, 0.81], 'box', [0.025, 0.025, 0.02], [1, 0, 0, 1])
        yellow_cube = create_item([0.22, -0.1, 0.8], 'box', [0.025, 0.025, 0.02], [1, 1, 0, 1])
        green_cube_1 = create_item([0.32, 0.1, 0.8], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])
        green_cube_2 = create_item([0.8, 0.0, 0.8], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])

        self.robot_id = {
            "robot1": robot_id_1,
            "robot2": robot_id_2,
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

