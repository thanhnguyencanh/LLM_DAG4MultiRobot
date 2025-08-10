from namex import export

from robot import robot_action
from collections import defaultdict
import json
import pybullet as p
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
task_plan = [
    ("robot", "pick cake"),
    ("robot", "place cake in Box2"),
    ("human", "pick teddy bear"),
    ("human", "place teddy bear in Box1"),
    ("robot", "pick toy car"),
    ("robottohuman", "move toy car to human"),
    ("human", "pick toy car"),
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
        last_task_for_object = {}
        for i, (agent, action) in enumerate(self.task_plan, start=1):
            parsed = self._parse_action(action)
            self.tasks[i] = {"agent": agent, "action": action, **parsed}

            obj = parsed["object"]

            # Lane tracking
            if agent == "human":
                self.lane_human.append(i)
            elif agent == "robot":
                self.lane_robot.append(i)

            # Handoff nodes
            if agent in ["robottohuman", "humantorobot"]:
                if obj and obj in last_task_for_object:
                    self.edges.append((last_task_for_object[obj], i))
                handoff_tracker[agent] = i

            # Normal dependency (pick/place/move nhưng không phải handoff nhận)
            elif not (
                    (agent == "human" and handoff_tracker["robottohuman"]) or
                    (agent == "robot" and handoff_tracker["humantorobot"])
            ):
                if obj and obj in last_task_for_object:
                    self.edges.append((last_task_for_object[obj], i))

            # Receiving from handoff
            if agent == "human" and handoff_tracker["robottohuman"]:
                self.edges.append((handoff_tracker["robottohuman"], i))
                handoff_tracker["robottohuman"] = None

            if agent == "robot" and handoff_tracker["humantorobot"]:
                self.edges.append((handoff_tracker["humantorobot"], i))
                handoff_tracker["humantorobot"] = None

            if obj:
                last_task_for_object[obj] = i

        orphaned = [k for k, v in handoff_tracker.items() if v is not None]
        if orphaned:
            raise ValueError(f"Orphaned handoffs: {orphaned}")

    def debug_print_graph(self):
        print("=== Danh sách node (ID, agent, action, verb, object, destination) ===")
        for tid, info in self.tasks.items():
            print(f"Node {tid}: {info}")

        print("\n=== Danh sách dependency (edges) ===")
        for u, v in self.edges:
            print(f"{u} -> {v}")

        print("\n=== Lane của agent ===")
        print(f"Lane robot: {self.lane_robot}")
        print(f"Lane human: {self.lane_human}")


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


def run_from_json(json_file, robot_ids, object_map, basket):
    with open(json_file) as f:
        cmds = json.load(f)

    current_constraint = None

    for c in cmds:
        agent = c.get('agent', '').lower()
        action = c.get('action', '').lower()
        obj = c.get('object', '').lower().strip()
        dst = c.get('destination', '').lower().strip()

        if agent not in robot_ids:
            print(f"[WARN] Agent '{agent}' không tồn tại trong robot_ids")
            continue

        this_robot_id = robot_ids[agent]

        robot_pos = [0.8, 0.2, 0.65]
        human_pos = [0.3, -0.2, 0.65]

        target_key = None
        # Lấy target_key ưu tiên obj, nếu không có obj thì dùng dst
        if obj:
            if obj in object_map:
                target_key = obj
            else:
                print(f"[WARN] Không tìm thấy object hợp lệ: obj='{obj}'")
                continue
        elif dst:
            if dst in object_map or dst in basket:
                target_key = dst
            elif dst in robot_ids:
                # Ví dụ dst = 'robot' hoặc 'human', target_key để None (điều kiện riêng)
                target_key = None
            else:
                print(f"[WARN] Không tìm thấy destination hợp lệ: dst='{dst}'")
                continue
        else:
            print(f"[WARN] Cả object và destination đều không hợp lệ hoặc rỗng: obj='{obj}', dst='{dst}'")
            continue

        if action == 'pick':
            if target_key is None:
                print(f"[WARN] Pick action nhưng không có target_key hợp lệ.")
                continue
            pos = robot_action.get_position(object_map[target_key])
            current_constraint = robot_action.pick(this_robot_id, object_map[target_key], pos)

        elif action == 'move' and dst == 'robot':
            # Di chuyển đến vị trí robot_pos, dùng move_to_target
            robot_action.move_to_target(this_robot_id, robot_pos, current_constraint)
            # Sau khi move, nếu còn vật kẹp thì thả xuống human_pos
            if current_constraint is not None:
                robot_action.place(agent, human_pos, current_constraint, robot_ids)
                current_constraint = None

        elif action == 'move' and dst == 'human':
            robot_action.move_to_target(this_robot_id, human_pos, current_constraint)
            if current_constraint is not None:
                robot_action.place(agent, robot_pos, current_constraint, robot_ids)
                current_constraint = None

        elif action == 'place':
            if target_key is None:
                print(f"[WARN] Place action nhưng không có target_key hợp lệ.")
                continue
            if dst in basket:
                pos = basket[dst]["center"]
            else:
                pos = robot_action.get_position(object_map[target_key])
            robot_action.place(agent, pos, current_constraint, robot_ids)
            current_constraint = None


tp = TaskProcessor(task_plan)
tp.debug_print_graph()
