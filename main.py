import pybullet as p
import cv2
import time
from simulation import environment
from robot import robot_action

p.connect(p.GUI)
p.setRealTimeSimulation(0)

robot_id, target_basket, objects = environment.setup_simulation()
view_matrix, projection_matrix = environment.get_camera_matrices()

camera_target_pos = [0.5, 0.0, 0.6]
camera_distance = 1.4
camera_yaw = 180
camera_pitch = -40
p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)

for _ in range(240):
    p.stepSimulation()
    time.sleep(1./240.)

target_item = "banana"
target_pos = target_basket
place_pos = target_pos['basket1']['center']
pick = False

while True:
    p.stepSimulation()
    obj_pos = robot_action.get_position(objects[target_item])
    if not pick:
        cid = robot_action.pick(robot_id, objects[target_item], obj_pos)
        robot_action.place(robot_id, place_pos, cid)
        pick = True

    time.sleep(1. / 240.)
    keys = p.getKeyboardEvents()
    if ord('q') in keys and keys[ord('q')] & p.KEY_WAS_TRIGGERED:
        break

    width, height, rgbImg, depthImg, _ = p.getCameraImage(
        width=640,
        height=480,
        viewMatrix=view_matrix,
        projectionMatrix=projection_matrix,
        renderer=p.ER_BULLET_HARDWARE_OPENGL
    )

cv2.destroyAllWindows()
p.disconnect()
