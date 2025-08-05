from Human_Robot_Colab.robot import robot_action
from collections import defaultdict
import json
import pybullet as p

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

class TaskProcessor:
    def __init__(self, task_plan):
        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self.lane_human = []
        self.lane_robot = []
        self._process_tasks()

    def _process_tasks(self):
        handoff_tracker = {"robottohuman": None, "humantorobot": None}

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            self.tasks[i] = {
                "agent": agent,
                "action": action,
                **self._parse_action(action)
            }

            if agent == "human":
                self.lane_human.append(i)
                if handoff_tracker["robottohuman"]:
                    self.edges.append((handoff_tracker["robottohuman"], i))
                    handoff_tracker["robottohuman"] = None

            elif agent == "robot":
                self.lane_robot.append(i)
                if handoff_tracker["humantorobot"]:
                    self.edges.append((handoff_tracker["humantorobot"], i))
                    handoff_tracker["humantorobot"] = None

            elif agent in ["robottohuman", "humantorobot"]:
                handoff_tracker[agent] = i

            if i > 1:
                prev_agent = self.tasks[i - 1]["agent"]
                if prev_agent == agent and agent in ["human", "robot"]:
                    self.edges.append((i - 1, i))

        orphaned = [k for k, v in handoff_tracker.items() if v is not None]
        if orphaned:
            raise ValueError(f"Orphaned handoffs: {orphaned}")

    def _parse_action(self, action_text):
        if not action_text:
            return {"verb": "unknown", "object": "", "destination": None}

        action_text = action_text.strip().lower()

        if action_text.startswith("move "):
            parts = action_text[5:].split(" to ")
            if len(parts) == 2:
                return {"verb": "move", "object": parts[0].strip(), "destination": parts[1].strip()}
            return {"verb": "move", "object": parts[0].strip(), "destination": None}

        elif action_text.startswith("place "):
            parts = action_text[6:].split(" in ")
            if len(parts) == 2:
                return {"verb": "place", "object": parts[0].strip(), "destination": parts[1].strip()}
            return {"verb": "place", "object": parts[0].strip(), "destination": None}

        elif action_text.startswith("pick "):
            return {"verb": "pick", "object": action_text[5:].strip(), "destination": None}

        return {"verb": "unknown", "object": action_text, "destination": None}

    def _get_ready_tasks(self, visited_set, prev_map):
        return [tid for tid in sorted(self.tasks.keys())
                if tid not in visited_set and
                all(dep in visited_set for dep in prev_map[tid])]

    def generate_commands(self):

        prev_map = defaultdict(set)
        for u, v in self.edges:
            prev_map[v].add(u)

        visited = set()
        current_agent = None
        current_group = []

        def flush():
            nonlocal current_group, current_agent
            if current_group:
                print(f"{current_agent.capitalize()}: {', '.join(current_group)}")
                current_group = []

        while len(visited) < len(self.tasks):
            ready_tasks = self._get_ready_tasks(visited, prev_map)
            if not ready_tasks:
                break

            tid = ready_tasks[0]
            task = self.tasks[tid]
            agent = task["agent"]

            if agent in ["robottohuman", "humantorobot"]:
                flush()
                move_agent = "robot" if agent == "robottohuman" else "human"
                target = "human" if agent == "robottohuman" else "robot"
                print(f"{move_agent.capitalize()}: move({target})")
                visited.add(tid)
                current_agent = None
                continue

            if current_agent != agent:
                flush()
                if current_agent == "human" and agent == "robot":
                    print("Press Enter to confirm human tasks completed...")
                    input()
                current_agent = agent

            verb = task["verb"]
            obj = task["object"]
            dest = task["destination"]

            if verb == "move":
                cmd = f"move({dest or obj})"
            elif verb == "pick":
                cmd = f"pick({obj})"
            elif verb == "place":
                cmd = f"place({dest or obj})"
            else:
                cmd = task["action"]

            current_group.append(cmd)
            visited.add(tid)

        flush()

    def export_json(self, filename="commands.json"):
        prev_map = defaultdict(set)
        for u, v in self.edges:
            prev_map[v].add(u)

        visited = set()
        json_list = []
        cmd_id = 1

        while len(visited) < len(self.tasks):
            ready_tasks = self._get_ready_tasks(visited, prev_map)
            if not ready_tasks:
                break

            tid = ready_tasks[0]
            task = self.tasks[tid]
            agent = task["agent"]

            if agent in ["robottohuman", "humantorobot"]:
                move_agent = "robot" if agent == "robottohuman" else "human"
                target = "human" if agent == "robottohuman" else "robot"
                json_list.append({
                    "id": cmd_id,
                    "agent": move_agent,
                    "action": "move",
                    "object": "",
                    "destination": target
                })
            else:
                json_list.append({
                    "id": cmd_id,
                    "agent": agent,
                    "action": task["verb"],
                    "object": task["object"] or "",
                    "destination": task["destination"] or ""
                })

            cmd_id += 1
            visited.add(tid)

        with open(filename, "w") as f:
            json.dump(json_list, f, indent=4)
        print(f"JSON command file saved to {filename}")


def run_from_json(json_file, robot_id, object_map, basket):
    with open(json_file) as f:
        cmds = json.load(f)

    current_constraint = None
    for c in cmds:
        agent = c['agent']
        action = c['action']
        obj = c['object'].lower()
        dst = c['destination'].lower()

        if agent != "robot":
            continue

        if action == 'pick':
            pos = robot_action.get_position(object_map[obj])
            current_constraint = robot_action.pick(robot_id, object_map[obj], pos)

        elif action == 'move' and dst == 'robot':
            receive_pos = [0.4, 0.2, 0.65]
            p.resetBasePositionAndOrientation(object_map[obj], receive_pos, [0, 0, 0, 1])
        elif action == 'move' and dst == 'human':
            human_pos = [0.6, -0.2, 0.65]
            robot_action.move_to_human(robot_id, human_pos, current_constraint)
            current_constraint = None
        elif action == 'place':
            if dst in basket:
                pos = basket[dst]["center"]
            else:
                pos = robot_action.get_position(object_map[dst])
            robot_action.place(robot_id, pos, current_constraint)
            current_constraint = None

