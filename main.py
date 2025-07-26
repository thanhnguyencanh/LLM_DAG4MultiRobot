
import pybullet as p
import cv2
import time
from simulation import environment
from robot import robot_action

p.connect(p.GUI)
p.setRealTimeSimulation(0)

robot_id, basket_ids, objects= environment.setup_simulation()
view_matrix, projection_matrix = environment.get_camera_matrices()

# Trong hàm setup_simulation hoặc sau khi load xong robot
camera_target_pos = [0.5, 0.0, 0.6]         # Nhìn vào giữa bàn/robot
camera_distance = 1.3                       # Khoảng cách camera
camera_yaw = 180                            # Góc xoay quanh trục Z (180 = nhìn từ phía trước vào)
camera_pitch = -30                          # Góc nghiêng xuống
p.resetDebugVisualizerCamera(camera_distance, camera_yaw, camera_pitch, camera_target_pos)

for _ in range(240):
    p.stepSimulation()
    time.sleep(1./240.)

target_item = "banana"
pick = False

while True:
    p.stepSimulation()
    target_pos = robot_action.get_object_position(objects[target_item])
    if not pick:
        robot_action.pick(robot_id, objects[target_item], target_pos)
        pick = True

    time.sleep(1. / 240.)
    keys = p.getKeyboardEvents()
    if ord('q') in keys and keys[ord('q')] & p.KEY_WAS_TRIGGERED:
        print("Dừng mô phỏng.")
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
