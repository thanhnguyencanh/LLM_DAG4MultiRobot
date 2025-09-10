import os

# Lấy root path của project (chứa main.py, robot/, my_objects/)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Robot URDF
ROBOT_URDF = os.path.join(PROJECT_ROOT, "robot", "ur5_robotiq_85.urdf")

# Bowls URDF
BOWL_GREEN_URDF = os.path.join(PROJECT_ROOT, "my_objects", "bowl_green", "bowl_green.urdf")
BOWL_RED_URDF   = os.path.join(PROJECT_ROOT, "my_objects", "bowl_red", "google_16k", "bowl_red.urdf")
BOWL_YELLOW_URDF = os.path.join(PROJECT_ROOT, "my_objects", "bowl_yellow", "google_16k", "bowl_yellow.urdf")
