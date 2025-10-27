import pybullet as p
import cv2
from Task2 import environment
from graph.execute_command import run_from_json
import time

#Sort the cubes in the correct bowl

def main():
    p.connect(p.GUI)
    p.setRealTimeSimulation(0)

    env = environment.Environment()
    env.setup_simulation()

    robot_ids = env.robot_id

    object_map = {}
    object_map.update(env.objects)

    camera_target_pos = [0.5, 0.0, 0.6]
    camera_distance = 1.4
    camera_yaw = 180
    camera_pitch = -40
    p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)

    run_from_json(
        "../task_plan_truth /commands_task2.json",
        robot_ids,
        object_map
    )
    time.sleep(3)
    cv2.destroyAllWindows()
    p.disconnect()


if __name__ == "__main__":
    main()
