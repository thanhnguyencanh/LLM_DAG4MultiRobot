import logging
import os
import time
import math
from configparser import ConfigParser
import numpy as np
from xarm.wrapper import XArmAPI

logger = logging.getLogger(__name__)

# Home joint angles in degrees (converted from simulation home_joints in radians)
HOME_JOINTS_DEG = [
    math.degrees(0.0),      # -90.0
    math.degrees(math.pi / 15),      # 12.0
    math.degrees(-2 * math.pi / 9),   # -40.0
    math.degrees(math.pi),            #  180.0
    math.degrees(2 * math.pi / 7),    #  51.4
    0.0,
]

# Home position in Cartesian coordinates [x, y, z, roll, pitch, yaw] (mm, degrees)
# You may need to adjust this based on your robot's actual home position
HOME_POSITION = [300, 0, 400, 180, 0, 0]


CONF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robot.conf')
parser = ConfigParser()
parser.read(CONF_PATH)
ROBOT_IP = parser.get('xArm', 'ip')

class UF850:
    def __init__(self, ip, speed=30):
        """
        Args:
            ip: Robot IP address.
            speed: Default joint speed in deg/s.
        """
        self.ip = ip
        self.speed = speed
        self.arm = None

    def connect(self):
        self.arm = XArmAPI(self.ip)
        self.arm.motion_enable(enable=True)
        self.arm.set_mode(0)
        self.arm.set_state(state=0)
        logger.info(f"Connected to UF850 at {self.ip}")

    def disconnect(self):
        if self.arm:
            self.arm.disconnect()
            logger.info("Disconnected")

    def go_home(self, speed=None, wait=True):
        """Move to home joint configuration."""
        self.set_joints(HOME_JOINTS_DEG, speed=speed, wait=wait)
        logger.info("Moved to home position")

    def set_joints(self, angles_deg, speed=None, wait=True):
        """Move to target joint positions (degrees).

        Args:
            angles_deg: List of 6 joint angles in degrees.
            speed: Joint speed in deg/s. Uses default if None.
            wait: Block until motion completes.
        """
        speed = speed or self.speed
        ret = self.arm.set_servo_angle(
            angle=list(angles_deg),
            speed=speed,
            wait=wait,
        )
        if ret != 0:
            logger.warning(f"set_servo_angle returned {ret}")
        return ret

    def set_joints_rad(self, angles_rad, speed=None, wait=True):
        """Move to target joint positions (radians).

        Args:
            angles_rad: List of 6 joint angles in radians.
            speed: Joint speed in deg/s. Uses default if None.
            wait: Block until motion completes.
        """
        angles_deg = [math.degrees(a) for a in angles_rad]
        return self.set_joints(angles_deg, speed=speed, wait=wait)

    def get_joints(self):
        """Get current joint positions in degrees.

        Returns:
            np.ndarray of shape (6,) with joint angles in degrees.
        """
        ret, angles = self.arm.get_servo_angle()
        if ret != 0:
            logger.warning(f"get_servo_angle returned {ret}")
        return np.array(angles[:6])

    def get_joints_rad(self):
        """Get current joint positions in radians.

        Returns:
            np.ndarray of shape (6,) with joint angles in radians.
        """
        return np.deg2rad(self.get_joints())

    def get_position(self):
        """Get current end-effector position [x, y, z, roll, pitch, yaw].

        Returns:
            np.ndarray of shape (6,).
        """
        ret, pose = self.arm.get_position()
        if ret != 0:
            logger.warning(f"get_position returned {ret}")
        return np.array(pose[:6])

    def set_position(self, pose, speed=None, wait=True):
        """Move to target Cartesian position.

        Args:
            pose: [x, y, z, roll, pitch, yaw] in mm and degrees.
            speed: Cartesian speed in mm/s. Uses default if None.
            wait: Block until motion completes.
        """
        speed = speed or self.speed * 10  # Convert to mm/s (approximate)
        ret = self.arm.set_position(
            x=pose[0], y=pose[1], z=pose[2],
            roll=pose[3], pitch=pose[4], yaw=pose[5],
            speed=speed,
            wait=wait,
        )
        if ret != 0:
            logger.warning(f"set_position returned {ret}")
        return ret

    def set_position_xyz(self, x=None, y=None, z=None, roll=None, pitch=None, yaw=None, speed=None, wait=True):
        """Move to target Cartesian position with optional parameters.

        Args:
            x, y, z: Position in mm. None keeps current value.
            roll, pitch, yaw: Orientation in degrees. None keeps current value.
            speed: Cartesian speed in mm/s.
            wait: Block until motion completes.
        """
        current = self.get_position()
        pose = [
            x if x is not None else current[0],
            y if y is not None else current[1],
            z if z is not None else current[2],
            roll if roll is not None else current[3],
            pitch if pitch is not None else current[4],
            yaw if yaw is not None else current[5],
        ]
        return self.set_position(pose, speed=speed, wait=wait)

    def go_home_position(self, speed=None, wait=True):
        """Move to home Cartesian position."""
        self.set_position(HOME_POSITION, speed=speed, wait=wait)
        logger.info("Moved to home position (Cartesian)")

    def init_gripper(self):
        """Initialize the gripper for use."""
        self.arm.set_gripper_mode(0)
        self.arm.set_gripper_enable(True)
        self.arm.set_gripper_speed(5000)
        logger.info("Gripper initialized")

    def open_gripper(self, position=420, wait=True, speed=None):
        """Open the gripper.

        Args:
            position: Gripper position (0=closed, 850=fully open).
            wait: Wait until motion completes.
            speed: Gripper speed. Uses default if None.
        """
        ret = self.arm.set_gripper_position(position, wait=wait, speed=speed)
        logger.info(f"Gripper OPENED to position {position}")
        print(f"Gripper: OPENED ({position})")
        return ret

    def close_gripper(self, position=0, wait=True, speed=None):
        """Close the gripper.

        Args:
            position: Gripper position (0=closed, 850=fully open).
            wait: Wait until motion completes.
            speed: Gripper speed. Uses default if None.
        """
        ret = self.arm.set_gripper_position(position, wait=wait, speed=speed)
        logger.info(f"Gripper CLOSED to position {position}")
        print(f"Gripper: CLOSED ({position})")
        return ret

    def get_gripper_position(self):
        """Get the current gripper position.

        Returns:
            int: Gripper position (0=closed, 850=fully open).
        """
        ret, pos = self.arm.get_gripper_position()
        print(f"Gripper position: {pos}")
        return pos

    def play_trajectory(self, trajectory_deg, speed=None, interval=0.0):
        """Execute a sequence of joint positions.

        Args:
            trajectory_deg: Array of shape (N, 6), each row is joint angles in degrees.
            speed: Joint speed in deg/s.
            interval: Delay in seconds between waypoints.
        """
        for i, joints in enumerate(trajectory_deg):
            logger.info(f"Waypoint {i+1}/{len(trajectory_deg)}: {joints}")
            self.set_joints(joints, speed=speed, wait=True)
            if interval > 0:
                time.sleep(interval)

    def descend_until_contact(self, force_threshold=5, step_mm=0.25, speed=100):
        """Descend in Z until the force sensor exceeds the threshold.

        Args:
            force_threshold: Force in N to detect contact (positive value).
            step_mm: Step size in mm per iteration.
            speed: Cartesian speed in mm/s.
        Returns:
            bool: True if contact detected, False if error.
        """
        # Enable F/T sensor and zero it
        self.arm.ft_sensor_enable(1)
        time.sleep(0.5)
        self.arm.ft_sensor_set_zero()
        time.sleep(0.3)

        # Switch to servo mode for real-time cartesian control
        self.arm.set_mode(1)
        self.arm.set_state(0)
        time.sleep(0.1)

        mvpose = list(self.get_position())
        contact = False

        while self.arm.connected and self.arm.state != 4:
            fz = self.arm.ft_ext_force[2]
            print(f"Z={mvpose[2]:.1f}mm, Fz={fz:.2f}N")

            if fz <= -force_threshold:
                print(f"Contact detected! Fz={fz:.2f}N <= -{force_threshold}N")
                contact = True
                break

            mvpose[2] -= step_mm
            ret = self.arm.set_servo_cartesian(mvpose, speed=speed, mvacc=2000)
            if ret != 0:
                print(f"set_servo_cartesian error: {ret}")
                break
            time.sleep(0.01)

        # Back to position mode
        self.arm.ft_sensor_enable(0)
        self.arm.clean_error()
        self.arm.clean_warn()
        self.arm.set_mode(0)
        self.arm.set_state(0)
        return contact

    def pick_object(self, pick_pos, place_pos=None, hover_height=100,
                    force_threshold=5, speed=None):
        """Pick object at 3D position and optionally place it at a destination.

        Args:
            pick_pos: [x, y, z, roll, pitch, yaw] position of object in mm/degrees.
            place_pos: [x, y, z, roll, pitch, yaw] place destination. If None, just pick and lift.
            hover_height: Height above pick/place position for approach/retreat in mm.
            force_threshold: Force in N to detect contact.
            speed: Cartesian speed in mm/s.
        """
        speed = speed or self.speed * 10  # Convert to mm/s

        # Calculate hover position above pick location
        hover_pos = list(pick_pos)
        hover_pos[2] += hover_height

        # 1. Move to hover position above the object
        print(f"Moving to hover position: {hover_pos}")
        self.set_position(hover_pos, speed=speed, wait=True)

        # 2. Move close to object (approach position)
        approach_pos = list(pick_pos)
        approach_pos[2] += 0  # 20mm above object
        print(f"Approaching object: {approach_pos}")
        self.set_position(approach_pos, speed=speed, wait=True)

        # # 3. Descend until force contact
        # print("Descending until contact...")
        # contact = self.descend_until_contact(force_threshold=force_threshold)

        # if not contact:
        #     print("No contact detected, aborting pick")
        #     return False

        # 4. Close gripper to grasp object
        self.close_gripper()
        time.sleep(0.5)

        # 5. Lift up to hover position
        print("Lifting object...")
        self.set_position(hover_pos, speed=speed, wait=True)
        self.get_gripper_position()

        # 6. Move to place position and release
        if place_pos is not None:
            # Calculate hover above place
            place_hover = list(place_pos)
            place_hover[2] += hover_height

            print(f"Moving to place hover: {place_hover}")
            self.set_position(place_hover, speed=speed, wait=True)

            print(f"Lowering to place position: {place_pos}")
            self.set_position(place_pos, speed=speed, wait=True)

            print("Releasing object...")
            self.open_gripper()
            time.sleep(0.5)

            # 7. Retreat upward
            print("Retreating...")
            self.set_position(place_hover, speed=speed, wait=True)

        return True


# Predefined object positions in Cartesian coordinates [x, y, z, roll, pitch, yaw] (mm, degrees)
# NOTE: Adjust these positions based on your actual workspace setup
OBJECTS = {
    'green_cube':[316, 74.3, -54.4, 185.9, 1, -56.1],
    'red_cube': [387.5, -73.7, -58.1, 180, 0, -16.3],
    'blue_cube': [465.8, 108.3, -60.4, -178.3, 1.9, 56.9],
    'green_bowl': [542.5, -42.6, -33.3, 180, 0, 0],
    'red_bowl': [383, 246.4, -26.4, 180, 0, 0],
    'blue_bowl': [251.8, -131, -29.8, 180, 0, 0],
}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    robot = UF850(ip=ROBOT_IP, speed=30)
    robot.connect()
    robot.init_gripper()

    try:
        robot.open_gripper()  # Ensure gripper is open at start
        robot.go_home()

        # Print current position for reference
        print(f"Current position: {robot.get_position()}")

        # Select object to pick
        print("Available objects:", list(OBJECTS.keys()))
        # obj_name = input("Enter object name to pick: ").strip()
        obj_name = 'green_cube'
        if obj_name not in OBJECTS:
            print(f"Unknown object '{obj_name}'")
        else:
            robot.pick_object(
                pick_pos=OBJECTS[obj_name],
                place_pos=OBJECTS['green_bowl'],
                hover_height=100,
                force_threshold=5,
                speed=200,
            )

        robot.go_home()

        obj_name = 'red_cube'
        if obj_name not in OBJECTS:
            print(f"Unknown object '{obj_name}'")
        else:
            robot.pick_object(
                pick_pos=OBJECTS[obj_name],
                place_pos=OBJECTS['red_bowl'],
                hover_height=100,
                force_threshold=5,
                speed=200,
            )

        robot.go_home()
        time.sleep(10)

        # obj_name = 'blue_cube'
        # if obj_name not in OBJECTS:
        #     print(f"Unknown object '{obj_name}'")
        # else:
        #     robot.pick_object(
        #         pick_pos=OBJECTS[obj_name],
        #         place_pos=OBJECTS['blue_bowl'],
        #         hover_height=100,
        #         force_threshold=5,
        #         speed=200,
        #     )

        # robot.go_home()
    finally:
        robot.open_gripper()  # Release any held object
        robot.disconnect()
