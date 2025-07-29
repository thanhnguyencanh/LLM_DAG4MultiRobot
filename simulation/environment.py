import math
import pybullet as p
import pybullet_data
from simulation.objects_simu import create_basket, create_item

def setup_simulation():
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.81)

    plane_id = p.loadURDF("plane.urdf",[0,0,0],globalScaling=2.0)

    table_id = p.loadURDF("table/table.urdf", [0.5, 0, 0])  # vị trí có thể tùy chỉnh

    robot_id = p.loadURDF("franka_panda/panda.urdf", [0.0, 0.0, 0.65], useFixedBase=True)

    # Các object
    banana = create_item([0.4, -0.2, 0.65], 'cylinder', [0.015, 0.1], [1, 1, 0, 1])  # Chuối
    apple = create_item([0.5, 0.1, 0.65], 'sphere', [0.02], [1, 0, 0, 1])  # Táo
    book = create_item([0.8, 0.3, 0.65], 'box', [0.03, 0.03, 0.005], [0.5, 0.25, 0, 1])  # Sách
    pen = create_item([0.9, -0.3, 0.65], 'cylinder', [0.01, 0.1], [0, 0, 1, 1])  # Bút
    p.changeDynamics(banana, -1, lateralFriction=0.3)

    basket1_ids, basket1_center = create_basket([0.4, 0.3, 0.6])
    basket2_ids, basket2_center = create_basket([0.9, 0.3, 0.6])

    objects = {
        "banana": banana,
        "apple": apple,
        "book": book,
        "pen": pen,
    }
    basket = {
        "basket1": {"ids": basket1_ids, "center": basket1_center},
        "basket2": {"ids": basket2_ids, "center": basket2_center},
    }
    return robot_id, basket, objects


def get_camera_matrices():
    camera_target = [0.6, 0, 0.85]  # Tâm bàn, vị trí các hộp
    camera_pos = [0.6, 0, 1.5]      # Đặt cao phía trên nhìn xuống
    camera_up = [0, 1, 0]           # Vector "trên" của camera, để tránh xoay ngược ảnh

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

