import pybullet as p
import cv2
import os
from graph.execute_command import run_from_json
from Task1 import environment

#Sort the cubes in the correct bowl

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    p.connect(p.GUI)
    p.setRealTimeSimulation(0)
    env = environment.Environment()
    env.setup_simulation()
    robot_ids = env.robot_id

    object_map = {}
    object_map.update(env.objects)

    camera_target_pos = [0.5, 0.0, 0.6]
    camera_distance = 1.6
    camera_yaw = 180
    camera_pitch = -40
    p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)


    run_from_json(
        os.path.join(SCRIPT_DIR, "../task_plan_truth/commands_task_1.json"), #Define the command file to run
        robot_ids,
        object_map
    )

    cv2.destroyAllWindows()
    p.disconnect()
    print("Simulation finished.")


if __name__ == "__main__":
    main()
