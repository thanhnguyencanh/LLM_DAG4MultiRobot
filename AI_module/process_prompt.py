from Task2.environment import Environment
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
        You are an intelligent collaborative planner capable of cooperating with a human based on the agent’s manipulation capability and reachable workspace.
    Your mission is to perform task planning for human and robot, given the environment description and an overall task goal.
    Environment description:
    1) Task: "{task}"
    2) Objects : {objects}
    3) Reachability status: 
        HUMAN: {human_objects}
        ROBOT: {robot_objects}
    Capabilities:
        HUMAN: can perform ALL actions
        ROBOT: PICK(object): MOVE to object and pick up the object from table or environment. MOVE(location): move robot hand or base to a target location, PLACE(object, destination): place object currently held into or onto a reachable destination. SWEEP(surface, tool): wipe or clean a surface using an object currently held (e.g., sponge)
    
    You must follow the following criteria:
    1) Each step of the task plan must follow this syntax:
         <label>: <instruction>
        where <label> ∈ {{ human, robot, humantorobot, robottohuman}}
        human or robot: describes an action executed by that agent. For example, if human take this action, label is human.
        humantorobot or robottohuman: describes a **move action** between two agents that move to the designated position. This label occurs when the responsible agent for the task cannot directly reach or manipulate the object due to reachability or capability limitations, so the other agent must deliver the object via a handover. For example, when the task is to chop a cucumber but the human cannot reach it, while the robot can. The robot must pick up the cucumber and move to the designated handover position. The plan will be: ("robottohuman": "move cucumber to human")
    
    2) Every "place" action must be preceded by a corresponding "pick" action of the same object. This ensures that the agent actually has the object in hand before placing it into the destination. After the "place" action is executed, the object is no longer in the agent’s hand.
    3) If an object is not reachable by the agent responsible for the task, a "move" action must be included to transfer the object from the other agent who can reach it. This ensures that the object is physically accessible before any manipulation actions are attempted.
    4) Output ONLY the task plan. Do not add any explanation, commentary, or extra text.

    Here's an example input and response:
    INPUT:
    Task:  Clean the table. The fruits should into the plate. 
    Objects: ["sponge", "lemon", "apple", "plate"], 
    Reachability status: 
    HUMAN: sponge, apple
    ROBOT: plate, lemon
    
    RESPONSE:(MUST HAVE FOLLOW THE FORMAT)
    ("robot", "pick lemon"),
    ("robot", "place lemon on the plate"),
    ("human", "pick apple "),
    ("humantorobot", "move apple to robot"),
    ("robot", "pick apple"),
    ("robot", "place apple on the plate"),
    (“human”, “ pick sponge”),
    (“human”, “ sweep the table ”),
    """

    return prompt_template



