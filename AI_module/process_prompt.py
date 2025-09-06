from Task1.environment import Environment
import pybullet as p
import math


def build_prompt():
    env = Environment()
    objects = ", ".join(env.get_object_names())

    task = input("Input task: ")

    def reachability_analysis(objects):
        human_objects = []
        robot_objects = []

        human_pos = [1.35, 0.0, 0.8]
        robot_pos = [-0.35, 0.0, 0.8]

        for obj_name, obj_pos in objects.items():
            d_human = math.dist(obj_pos, human_pos)
            d_robot = math.dist(obj_pos, robot_pos)

            if d_human < d_robot:
                human_objects.append(obj_name)
            else:
                robot_objects.append(obj_name)

        return human_objects, robot_objects

    human_objects, robot_objects = reachability_analysis(env.objects)
    prompt_template = f"""
    You are an intelligent collaborative robot capable of cooperating with a human based on your manipulation capability and reachable workspace.
    Your mission is to perform task planning given the environment description and an overall task goal.

    Task: "{task}"

    There are some objects  on the table:
    {objects}

    Reachability status:
    HUMAN: {human_objects}
    ROBOT: {robot_objects}

    Capabilities:
    HUMAN: can perform ALL actions
    ROBOT: PICK, MOVE, PLACE, SWEEP

    Your goal is to generate a REASONABLE sequence of subtasks so that the robot and human can perform. ATTENTION to the Reachability status and Capabilities.
    Each step of the task plan must follow this syntax:
    <label>: <instruction>a
    where <label> ∈ {{ human, robot, humantorobot, robottohuman}}
    human or robot: describes an action executed by that agent
    humantorobot / robottohuman: describes a **move action** between agents that move to the handover position. If an agent can not reach objects, they need to move objects to another agent.
    IF “place” action must have “pick” action after that.

    Output ONLY the task plan. Do not add any explanation, commentary, or extra text.
    Example format:(MUST HAVE FOLLOW THE FORMAT)
    ("human", "chop a tomato"),
    ("robot", "place pot on stove"),
    ("humantorobot", "move chopped tomato to robot"),
    ("robot", "stir soup"),
    ("robottohuman", "move pot to the human"),
    """

    return prompt_template



