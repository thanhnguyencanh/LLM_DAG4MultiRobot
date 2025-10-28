import os

# Lấy root path của project (chứa main, robot/, my_objects/)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Robot URDF
ROBOT_URDF = os.path.join(PROJECT_ROOT, "robot", "ur5_robotiq_85.urdf")

# Task1
BOWL_GREEN_URDF = os.path.join(PROJECT_ROOT, "my_objects", "bowl_green", "bowl_green.urdf")
BOWL_RED_URDF   = os.path.join(PROJECT_ROOT, "my_objects", "bowl_red", "google_16k", "bowl_red.urdf")
BOWL_YELLOW_URDF = os.path.join(PROJECT_ROOT, "my_objects", "bowl_yellow", "google_16k", "bowl_yellow.urdf")

#Task2
TABLE_URDF      = os.path.join(PROJECT_ROOT, "my_objects", "circle_table", "ban.urdf")
#Taks 3
PLATE_URDF       = os.path.join(PROJECT_ROOT, "my_objects", "029_plate", "google_16k", "029_plate.urdf")
BANANA_URDF      = os.path.join(PROJECT_ROOT, "my_objects", "011_banana", "google_16k", "011_banana.urdf")
APPLE_URDF       = os.path.join(PROJECT_ROOT, "my_objects", "013_apple", "google_16k", "013_apple.urdf")
SPOON_URDF       = os.path.join(PROJECT_ROOT, "my_objects", "031_spoon", "google_16k", "031_spoon.urdf")
SPONGE_URDF      = os.path.join(PROJECT_ROOT, "my_objects", "026_sponge", "google_16k", "026_sponge.urdf")
DRAWER_URDF      = os.path.join(PROJECT_ROOT, "my_objects", "drawer", "urdf", "drawer.urdf")
ORANGE_CUP_URDF  = os.path.join(PROJECT_ROOT, "my_objects", "065-a_cups", "google_16k", "065-a_cups.urdf")
PURPLE_CUP_URDF  = os.path.join(PROJECT_ROOT, "my_objects", "065-f_cups", "google_16k", "065-f_cups.urdf")

