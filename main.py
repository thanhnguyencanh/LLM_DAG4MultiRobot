import pybullet as p
import cv2
from simulation import environment
from Human_Robot_Colab.graph.graph_comannd import run_from_json

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

    object_map = {'cake': 'cake', 'apple': 'apple', 'box1': 'box1', 'box2': 'box2','teddy_bear': 'teddy_bear','toy_car': 'toy_car'}
    object_map = objects.copy()
    for name, info in target_basket.items():
        object_map[name.lower()] = info["ids"]

    run_from_json("commands.json", robot_id, object_map, target_basket)

    cv2.destroyAllWindows()
    p.disconnect()
    print("Simulation kết thúc.")


if __name__ == "__main__":
    main()

