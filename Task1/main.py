import pybullet as p
import cv2
from graph.execute_command import run_from_json
from Task1 import environment

#Sort the cubes into bowls with true color.
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
        "commands_task1.json",
        robot_ids,
        object_map
    )

    cv2.destroyAllWindows()
    p.disconnect()
    print("Simulation kết thúc.")


if __name__ == "__main__":
    main()
