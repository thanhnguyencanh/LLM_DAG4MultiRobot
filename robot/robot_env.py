import pybullet as p
import math
from collections import namedtuple
import pybullet_data
from paths import ROBOT_URDF


class UR5Robotiq85:
    """
    UR5 Robot with Robotiq 85 Gripper controller class.
    Handles robot loading, inverse kinematics, and gripper control.
    """
    
    def __init__(self, pos, ori):
        """
        Initialize robot with base position and orientation.
        
        Args:
            pos: [x, y, z] base position
            ori: [roll, pitch, yaw] base orientation in radians
        """
        self.base_pos = pos
        self.base_ori = p.getQuaternionFromEuler(ori)
        self.eef_id = 7  # End-effector link index
        self.arm_num_dofs = 6  # 6 degrees of freedom for UR5
        self.arm_rest_poses = [0.0, -1.57, 1.57, -1.5, -1.57, 0.0]  # Home position
        self.gripper_range = [0, 0.085]  # Gripper open range in meters
        self.max_velocity = 3  # Max joint velocity

    def load(self):
        """Load robot URDF and initialize joints to rest position."""
        self.id = p.loadURDF(
            str(ROBOT_URDF),
            self.base_pos,
            self.base_ori,
            useFixedBase=True
        )
        self.__parse_joint_info__()  # Get joint information of the robot arm
        self.__setup_mimic_joints__()  # Set up mimic joints for the gripper
        
        # Reset arm joints to rest pose
        for i, joint_id in enumerate(self.arm_controllable_joints):
            if i < len(self.arm_rest_poses):
                p.resetJointState(self.id, joint_id, self.arm_rest_poses[i])

    def __parse_joint_info__(self):
        """Parse joint information from URDF and identify controllable joints."""

        jointInfo = namedtuple('jointInfo',
                               ['id', 'name', 'type', 'lowerLimit', 'upperLimit', 'maxForce', 'maxVelocity', 'controllable'])
        self.joints = []
        self.controllable_joints = []

        for i in range(p.getNumJoints(self.id)):
            info = p.getJointInfo(self.id, i)
            jointID = info[0]
            jointName = info[1].decode("utf-8")
            jointType = info[2]
            jointLowerLimit = info[8]
            jointUpperLimit = info[9]
            jointMaxForce = info[10]
            jointMaxVelocity = info[11]
            controllable = jointType != p.JOINT_FIXED
            if controllable:
                self.controllable_joints.append(jointID)
            self.joints.append(
                jointInfo(jointID, jointName, jointType, jointLowerLimit, jointUpperLimit, jointMaxForce, jointMaxVelocity, controllable)
            )

        self.arm_controllable_joints = self.controllable_joints[:self.arm_num_dofs]
        self.arm_lower_limits = [j.lowerLimit for j in self.joints if j.controllable][:self.arm_num_dofs]
        self.arm_upper_limits = [j.upperLimit for j in self.joints if j.controllable][:self.arm_num_dofs]
        self.arm_joint_ranges = [ul - ll for ul, ll in zip(self.arm_upper_limits, self.arm_lower_limits)]

    def __setup_mimic_joints__(self):

        mimic_parent_name = 'finger_joint'
        mimic_children_names = {
            'right_outer_knuckle_joint': 1,
            'left_inner_knuckle_joint': 1,
            'right_inner_knuckle_joint': 1,
            'left_inner_finger_joint': -1,
            'right_inner_finger_joint': -1
        }
        self.mimic_parent_id = [joint.id for joint in self.joints if joint.name == mimic_parent_name][0]
        self.mimic_child_multiplier = {joint.id: mimic_children_names[joint.name] for joint in self.joints if joint.name in mimic_children_names}

        for joint_id, multiplier in self.mimic_child_multiplier.items():
            c = p.createConstraint(self.id, self.mimic_parent_id, self.id, joint_id,
                                   jointType=p.JOINT_GEAR, jointAxis=[0, 1, 0],
                                   parentFramePosition=[0, 0, 0], childFramePosition=[0, 0, 0])
            p.changeConstraint(c, gearRatio=-multiplier, maxForce=100, erp=1)

    def move_arm_ik(self, target_pos, target_orn):
        """
        Move arm to target position using Inverse Kinematics.
        
        Args:
            target_pos: [x, y, z] target end-effector position
            target_orn: quaternion [x, y, z, w] target orientation
        """
        joint_poses = p.calculateInverseKinematics(
            self.id, self.eef_id, target_pos, target_orn,
            lowerLimits=self.arm_lower_limits,
            upperLimits=self.arm_upper_limits,
            jointRanges=self.arm_joint_ranges,
            restPoses=self.arm_rest_poses,
        )
        # Apply joint positions with velocity control
        for i, joint_id in enumerate(self.arm_controllable_joints):
            p.setJointMotorControl2(self.id, joint_id, p.POSITION_CONTROL, joint_poses[i], maxVelocity=self.max_velocity)

    def move_gripper(self, open_length):
        """
        Control gripper opening.
        
        Args:
            open_length: Opening distance in meters (0 = closed, 0.085 = fully open)
        """
        open_length = max(self.gripper_range[0], min(open_length, self.gripper_range[1]))
        # Convert linear opening to joint angle using gripper geometry
        open_angle = 0.715 - math.asin((open_length - 0.010) / 0.1143)
        p.setJointMotorControl2(self.id, self.mimic_parent_id, p.POSITION_CONTROL, targetPosition=open_angle)









