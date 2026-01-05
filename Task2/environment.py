from robot.robot_env import UR5Robotiq85
import pybullet as p
import pybullet_data
from paths import TABLE_URDF,BOWL_GREEN_URDF, BOWL_RED_URDF, BOWL_YELLOW_URDF
from my_objects.objects_simu import create_item
class Environment:
    def __init__(self):
        self.robot_id = {}
        self.basket = {}
        self.objects = {
            "green_bowl": (0.5, -0.3, 0.3),
            "yellow_bowl": (0.95, 0.85, 0.3),
            "red_bowl": (-0.2, 0.35, 0.3),
            "red_cube_1": (0.2, 0.7, 0.45),
            "red_cube_2": (1.2, 0.2, 0.45),
            "yellow_cube_1": (0.9, 0.5, 0.45),
            "yellow_cube_2": (0.0, -0.3, 0.45),
            "green_cube_1": (0.4, 0.3, 0.45),
            "green_cube_2": (0.9, -0.3, 0.45),
            "green_cube_3": (0.1, 0.5, 0.45),
        }
        self.handoff_points = {
            "robot1torobot2": [0.95, -0.0464, 0.3],
            "robot2torobot1": [0.95, -0.0464, 0.3],
            "robot2torobot3": [0.55, 0.6464, 0.3],
            "robot3torobot2": [0.55, 0.6464, 0.3],
            "robot1torobot3": [0.1, 0.0, 0.3],
            "robot3torobot1": [0.1, 0.0, 0.3],
        }
        self.agent_positions = {
            "robot1": [0.5, -0.6928, 0.3],
            "robot2": [1.4, 0.6, 0.3],
            "robot3": [-0.3, 0.6928, 0.3],
        }

    def get_object_names(self):
        return list(self.objects.keys())

    def setup_simulation(self):
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -10)
        p.loadURDF("plane.urdf", [0, 0, 0], globalScaling=2.0)

        table = create_item(
            baseMass=0,
            position=[0.5, 0.0, 0.0],  # table surface position
            shape='cylinder',
            size=[1.2, 0.5],  # [radius, height]
            color=[0.5, 0.4, 0.2, 1]  # brown wood color
        )
        robot_id_1 = UR5Robotiq85([0.5, -0.6928, 0.3], [0, 0.0, 1.5])
        robot_id_1.load()
        robot_id_2 = UR5Robotiq85([1.4, 0.6, 0.3], [0, 0, -2.6])
        robot_id_2.load()
        robot_id_3 = UR5Robotiq85([-0.3, 0.6928, 0.3], [0.0, 0.0, -1.1])
        robot_id_3.load()

        green_bowl = p.loadURDF(BOWL_GREEN_URDF, [0.5, -0.3, 0.3], globalScaling=0.13)
        yellow_bowl = p.loadURDF(BOWL_YELLOW_URDF, [0.95, 0.85, 0.3], globalScaling=0.13)
        red_bowl = p.loadURDF(BOWL_RED_URDF, [-0.2, 0.35, 0.3], globalScaling=0.13)

        red_cube_1 = create_item([0.2, 0.7, 0.45], 'box', [0.025, 0.025, 0.02], [1, 0, 0, 1])
        red_cube_2 = create_item([1.2, 0.2, 0.45], 'box', [0.025, 0.025, 0.02], [1, 0, 0, 1])

        yellow_cube_1 = create_item([0.9, 0.5, 0.45], 'box', [0.025, 0.025, 0.02], [1, 1, 0, 1])
        yellow_cube_2 = create_item([0.0, -0.3, 0.45], 'box', [0.025, 0.025, 0.02], [1, 1, 0, 1])

        green_cube_1 = create_item([0.4, 0.3, 0.45], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])
        green_cube_2 = create_item([0.9, -0.3, 0.45], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])
        green_cube_3 = create_item([0.1, 0.5, 0.45], 'box', [0.025, 0.025, 0.025], [0, 1, 0, 1])

        self.robot_id = {
            "robot1": robot_id_1,
            "robot2": robot_id_2,
            "robot3": robot_id_3,
        }

        self.objects = {
            "red_cube_1": red_cube_1,
            "red_cube_2": red_cube_2,
            "yellow_cube_1": yellow_cube_1,
            "yellow_cube_2": yellow_cube_2,
            "green_cube_1": green_cube_1,
            "green_cube_2": green_cube_2,
            "green_bowl": green_bowl,
            "yellow_bowl": yellow_bowl,
            "red_bowl": red_bowl,
            "green_cube_3": green_cube_3,
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

