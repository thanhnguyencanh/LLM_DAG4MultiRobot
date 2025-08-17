import pybullet as p
import cv2
from Task1.simulation import environment
from graph.graph_comannd import run_from_json

def main():
    p.connect(p.GUI)
    p.setRealTimeSimulation(0)

    env = environment.Environment()
    env.setup_simulation()

    robot_id = env.robot_id
    target_basket = env.basket
    objects = env.objects

    camera_target_pos = [0.5, 0.0, 0.6]
    camera_distance = 1.4
    camera_yaw = 180
    camera_pitch = -40
    p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)

    run_from_json("commands.json", robot_id, objects, target_basket)

    cv2.destroyAllWindows()
    p.disconnect()
    print("Simulation kết thúc.")

if __name__ == "__main__":
    main()
