from Human_Robot_Colab import robot
import re
from collections import defaultdict
task_plan = [
    ("robot", "pick cake"),
    ("robot", "place cake in Box2"),
    ("human", "pick teddy bear"),
    ("human", "place teddy bear in Box1"),
    ("robot", "pick toy car"),
    ("robottohuman", "move toy car to human"),
    ("human", "place toy car in Box1"),
    ("human", "pick apple"),
    ("humantorobot", "move apple to robot"),
    ("robot", "pick apple"),
    ("robot", "place apple in Box2"),
]
def process(task_plan):
    tasks = {}
    lane_human = []
    lane_robot = []
    edges = []

    cross_buffer = {
        "robottohuman": None,
        "humantorobot": None
    }

    for i, (agent, action) in enumerate(task_plan, start=1):
        tasks[i] = {"agent": agent, "action": action}

        # Assign to lanes
        if agent == "human":
            lane_human.append(i)
        elif agent == "robot":
            lane_robot.append(i)
        elif agent == "robottohuman":
            cross_buffer["robottohuman"] = i
        elif agent == "humantorobot":
            cross_buffer["humantorobot"] = i

        # Add sequential dependencies within same agent
        if i > 1:
            prev_id = i - 1
            prev_agent = tasks[prev_id]["agent"]

            # Same agent sequential dependency
            if prev_agent == agent and agent in ["human", "robot"]:
                edges.append((prev_id, i))

        # Handle cross-agent handoff dependencies
        if agent == "human" and cross_buffer["robottohuman"]:
            edges.append((cross_buffer["robottohuman"], i))
            cross_buffer["robottohuman"] = None

        if agent == "robot" and cross_buffer["humantorobot"]:
            edges.append((cross_buffer["humantorobot"], i))
            cross_buffer["humantorobot"] = None

    return tasks, lane_human, lane_robot, edges


def semantic_parsing(action_text: str):
    if not action_text:
        return "unknown", "", None

    action_text = action_text.strip().lower()

    if action_text.startswith("move "):
        parts = action_text[5:].split(" to ")
        if len(parts) == 2:
            obj, dest = parts
            return "move", obj.strip(), dest.strip()
        else:
            return "move", parts[0].strip() if parts else "", None

    elif action_text.startswith("place "):
        parts = action_text[6:].split(" in ")
        if len(parts) == 2:
            obj, dest = parts
            return "place", obj.strip(), dest.strip()
        else:
            return "place", parts[0].strip() if parts else "", None

    elif action_text.startswith("pick "):
        obj = action_text[5:].strip()
        return "pick", obj, None

    else:
        return "unknown", action_text, None


def graph_to_command(tasks, edges):
    prev_map = defaultdict(set)
    for u, v in edges:
        prev_map[v].add(u)

    current_agent = None
    current_group = []
    visited = set()

    def flush():
        nonlocal current_group, current_agent
        if current_group:
            print(f"{current_agent.capitalize()}: {', '.join(current_group)}")
            current_group = []

    def check_continue():
           pass

    def get_ready_tasks(visited_set):
        ready = []
        for tid in sorted(tasks.keys()):
            if tid not in visited_set:
                if all(dep in visited_set for dep in prev_map[tid]):
                    ready.append(tid)
        return ready

    while len(visited) < len(tasks):
        ready_tasks = get_ready_tasks(visited)

        if not ready_tasks:
            break

        tid = ready_tasks[0]
        agent = tasks[tid]["agent"]
        action = tasks[tid]["action"]
        verb, obj, dest = semantic_parsing(action)

        if agent in ["robottohuman", "humantorobot"]:
            flush()
            if current_group:
                check_continue()
            if agent == "robottohuman":
                move_agent = "robot"
                move_cmd = f"move(human)"
            elif agent == "humantorobot":
                move_agent = "human"
                move_cmd = f"move(robot)"
            print(f"{move_agent.capitalize()}: {move_cmd}")
            print("Press Enter to confirm handoff completion...")
            input()
            visited.add(tid)
            current_agent = None
            continue

        needs_flush = (current_agent != agent or
                       (current_group and tid not in prev_map))

        if needs_flush:
            flush()
            if current_agent == "human" and agent == "robot":
                print("Press Enter to confirm human tasks completed...")
                input()
            current_agent = agent

        if verb == "move":
            cmd = f"move({dest})" if dest else f"move({obj})"
        elif verb == "pick":
            cmd = f"pick({obj})" if obj else "pick()"
        elif verb == "place":
            cmd = f"place({dest})" if dest else f"place({obj})"
        else:
            cmd = action

        current_group.append(cmd)
        visited.add(tid)

    flush()

def validate_task_plan(task_plan):
    issues = []

    # Check for orphaned handoffs
    handoff_map = {"robottohuman": False, "humantorobot": False}

    for i, (agent, action) in enumerate(task_plan):
        if agent in handoff_map:
            handoff_map[agent] = True
        elif agent in ["human", "robot"]:
            if i > 0:
                prev_agent = task_plan[i - 1][0]
                if ((agent == "human" and prev_agent == "robottohuman") or
                        (agent == "robot" and prev_agent == "humantorobot")):
                    handoff_map[prev_agent] = False

    for handoff, orphaned in handoff_map.items():
        if orphaned:
            issues.append(f"Orphaned handoff: {handoff}")

    if issues:
        print("Task plan validation issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Task plan validation: OK")

    return len(issues) == 0

def execute_command(command_str, robot_id, object_map):
    match = re.match(r"(\w+)\(([\w\s]+)(?:→([\w\s]+))?\)", command_str)
    if not match:
        print("Không hiểu lệnh:", command_str)
        return
    action, obj, dest = match.groups()
    obj = obj.strip()
    if dest:
        dest = dest.strip()

    obj_id = object_map.get(obj)
    dest_pos = object_map.get(dest)

    if action == "pick":
        target_pos = robot.robot_action.get_position(obj_id)
        robot.robot_action.pick(robot_id, obj_id, target_pos)

    elif action == "place":
        target_pos = robot.robot_action.get_position(dest_pos)
        robot.robot_action.place(robot_id, target_pos, constraint_id=None)

    elif action == "move":
        if dest == "human":
            pos = [0.6, -0.2, 0.65]
        elif dest == "robot":
            pos = [0.4, 0.2, 0.65]
        else:
            pos = robot.robot_action.get_position(object_map[dest])
        robot.robot_action.move_to_target(robot_id, pos)


