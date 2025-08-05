import pybullet as p
import cv2
import time
from simulation import environment
from robot import robot_action
from Human_Robot_Colab.task.sort_objects import execute_command, graph_to_command, process,task_plan,semantic_parsing
import re
def main():
    p.connect(p.GUI)
    p.setRealTimeSimulation(0)

    robot_id, target_basket, objects = environment.setup_simulation()
    view_matrix, projection_matrix = environment.get_camera_matrices()

    camera_target_pos = [0.5, 0.0, 0.6]
    camera_distance = 1.4
    camera_yaw = 180
    camera_pitch = -40
    p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)

    object_map = {
        "cake": objects.get("cake"),
        "teddy bear": objects.get("teddy_bear"),
        "toy car": objects.get("toy_car"),
        "apple": objects.get("apple"),
        "Box1": target_basket.get("Box1"),
        "Box2": target_basket.get("Box2"),
        "human": "human_position",
        "robot": "robot_position"
    }

    # Dọn dẹp
    cv2.destroyAllWindows()
    p.disconnect()
    print("Simulation kết thúc.")


if __name__ == "__main__":
    main()


