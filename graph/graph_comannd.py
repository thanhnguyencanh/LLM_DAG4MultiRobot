import threading
from robot import robot_action
from collections import defaultdict
import json

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
        self._process_tasks()

    def _process_tasks(self):
        """Xử lý task plan và tạo dependencies"""
        handoffs = {"robottohuman": None, "humantorobot": None}
        object_last_task = {}

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)
            self.tasks[i] = {"agent": agent, "action": action, "object": obj}

            # Tạo dependencies dựa trên object
            if obj and obj in object_last_task:
                self.edges.append((object_last_task[obj], i))

            # Xử lý handoff
            if agent in handoffs:
                handoffs[agent] = i
            elif agent == "human" and handoffs["robottohuman"]:
                self.edges.append((handoffs["robottohuman"], i))
                handoffs["robottohuman"] = None
            elif agent == "robot" and handoffs["humantorobot"]:
                self.edges.append((handoffs["humantorobot"], i))
                handoffs["humantorobot"] = None

            if obj:
                object_last_task[obj] = i

    def _extract_object(self, action):
        """Trích xuất object từ action"""
        action = action.lower()
        if "pick " in action:
            return action.split("pick ")[1].strip()
        elif "move " in action:
            return action.split("move ")[1].split(" to ")[0].strip()
        elif "place " in action:
            return action.split("place ")[1].split(" in ")[0].strip()
        return ""

    def assign_waves(self):
        """Gán wave cho các task"""
        # Tạo dependency map
        deps = defaultdict(set)
        for u, v in self.edges:
            deps[v].add(u)

        # Tìm chains
        chains = self._find_chains(deps)

        # Gán wave
        wave = 1
        for chain in chains:
            has_transfer = any(self.tasks[t]["agent"] in ["robottohuman", "humantorobot"] for t in chain)
            for task_id in chain:
                self.tasks[task_id]["wave"] = wave
            if has_transfer:
                wave += 1

        # Tasks không có transfer cùng wave 1
        if not any(self.tasks[t].get("wave") for t in self.tasks):
            for task_id in self.tasks:
                self.tasks[task_id]["wave"] = 1

    def _find_chains(self, deps):
        """Tìm các chains của tasks"""
        visited = set()
        chains = []

        # Tìm start nodes (không có dependency)
        start_nodes = [t for t in self.tasks if not deps[t]]

        for start in start_nodes:
            if start not in visited:
                chain = self._build_chain(start, deps, visited)
                if chain:
                    chains.append(chain)

        return chains

    def _build_chain(self, start, deps, visited):
        """Xây dựng chain từ một node"""
        chain = []
        queue = [start]

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue

            chain.append(node)
            visited.add(node)

            # Tìm nodes phụ thuộc vào node này
            for task_id, task_deps in deps.items():
                if node in task_deps and task_id not in visited:
                    queue.append(task_id)

        return sorted(chain)

    def export_json(self, filename="commands.json"):
        """Export thành JSON"""
        self.assign_waves()

        commands = []
        for task_id in sorted(self.tasks.keys()):
            task = self.tasks[task_id]
            agent = task["agent"]

            # Xử lý transfer agents
            if agent == "robottohuman":
                agent = "robot"
                lane = "transfer"
            elif agent == "humantorobot":
                agent = "human"
                lane = "transfer"
            else:
                lane = agent

            # Parse action
            verb, obj, dest = self._parse_action(task["action"])

            commands.append({
                "id": task_id,
                "agent": agent,
                "action": verb,
                "object": obj.replace(" ", "_") if obj else "",
                "destination": dest.replace(" ", "_") if dest else "",
                "lane": lane,
                "wave": task.get("wave", 1)
            })

        with open(filename, "w") as f:
            json.dump(commands, f, indent=2)
        print(f"Exported to {filename}")

    def _parse_action(self, action):
        """Parse action thành verb, object, destination"""
        action = action.lower()

        if action.startswith("pick "):
            return "pick", action[5:], ""
        elif action.startswith("place "):
            parts = action[6:].split(" in ")
            return "place", parts[0], parts[1] if len(parts) > 1 else ""
        elif action.startswith("move "):
            parts = action[5:].split(" to ")
            return "move", parts[0], parts[1] if len(parts) > 1 else ""

        return "unknown", action, ""


def run_from_json(json_file, robot_ids, object_map, basket):
    """Thực thi tasks từ JSON file"""
    with open(json_file) as f:
        commands = json.load(f)

    # Nhóm theo wave
    waves = defaultdict(list)
    for cmd in commands:
        waves[cmd["wave"]].append(cmd)

    # Thực thi từng wave
    for wave_id in sorted(waves.keys()):
        tasks = waves[wave_id]
        has_transfer = any(t["lane"] == "transfer" for t in tasks)

        if has_transfer:
            print(f"Wave {wave_id}: Sequential execution")
            _execute_sequential(tasks, robot_ids, object_map, basket)
        else:
            print(f"Wave {wave_id}: Parallel execution")
            _execute_parallel(tasks, robot_ids, object_map, basket)


def _execute_sequential(tasks, robot_ids, object_map, basket):
    """Thực thi tuần tự"""
    constraint = None

    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, basket, constraint)


def _execute_parallel(tasks, robot_ids, object_map, basket):
    # Nhóm theo agent
    agent_tasks = defaultdict(list)
    for task in tasks:
        agent_tasks[task["agent"]].append(task)

    # Tạo threads
    threads = []
    for agent, task_list in agent_tasks.items():
        thread = threading.Thread(target=_execute_agent_tasks,
                                  args=(agent, task_list, robot_ids, object_map, basket))
        threads.append(thread)
        thread.start()

    # Đợi hoàn thành
    for thread in threads:
        thread.join()


def _execute_agent_tasks(agent, tasks, robot_ids, object_map, basket):
    """Thực thi tasks của một agent"""
    constraint = None
    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, basket, constraint)


def _execute_task(task, robot_ids, object_map, basket, constraint):
    """Thực thi một task"""
    agent = task["agent"]
    action = task["action"]
    obj = task["object"]
    dest = task["destination"]

    if agent not in robot_ids:
        print(f"Unknown agent: {agent}")
        return constraint

    robot_id = robot_ids[agent]

    try:
        if action == "pick" and obj in object_map:
            pos = robot_action.get_position(object_map[obj])
            return robot_action.pick(robot_id, object_map[obj], pos)

        elif action == "place":
            if dest in basket:
                pos = basket[dest]["center"]
            else:
                pos = robot_action.get_position(object_map.get(obj, obj))
            robot_action.place(agent, pos, constraint, robot_ids)
            return None

        elif action == "move":
            target_pos = [0.3, -0.2, 0.65] if dest == "robot" else [0.8, 0.2, 0.65]
            robot_action.move_to_target(robot_id, target_pos, constraint)
            if constraint:
                robot_action.place(agent, target_pos, constraint, robot_ids)
                return None

    except Exception as e:
        print(f"Error executing {action} for {agent}: {e}")

    return constraint


