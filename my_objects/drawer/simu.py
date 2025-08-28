import pybullet as p
import pybullet_data
import time
import math

# Kết nối PyBullet
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())

# Thêm mặt đất
p.loadURDF("plane.urdf")

# Load cabinet
cabinet = p.loadURDF("urdf/tu.urdf", [0,0,0], useFixedBase=True)

# ID của joint ngăn kéo
drawer_joint = 0  

# Di chuyển ngăn kéo ra/vào
for t in range(500):
    pos = 0.15 * (1 + math.sin(t * 0.02))  # dao động ra/vào
    p.setJointMotorControl2(cabinet, drawer_joint,
                            controlMode=p.POSITION_CONTROL,
                            targetPosition=pos,
                            force=20)
    p.stepSimulation()
    time.sleep(1/240)

p.disconnect()
