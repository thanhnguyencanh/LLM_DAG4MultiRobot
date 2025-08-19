import threading
from collections import defaultdict
import json
from robot import robot_action

task_plan_2 = [
    ("human", "pick banana"),
    ("human", "place banana on plate"),

    ("robottohuman", "move apple to human"),
    ("human", "pick apple"),
    ("human", "place apple on plate"),

    ("human", "pick orange cup"),
    ("humantorobot", "move orange cup to robot"),
    ("robot", "pick orange cup into drawer"),
    ("robot", "place orange cup into drawer"),

    ("robot", "pick purple cup"),
    ("robot", "place purple cup into drawer"),

    ("robot", "pick spoon"),
    ("robot", "place spoon into drawer"),

    ("robot", "pick sponge"),
    ("robot", "sweep table with sponge")
]


class TaskProcessor:
    def __init__(self, task_plan):
        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self._process_tasks()

    def _process_tasks(self):
        handoffs = {"robottohuman": None, "humantorobot": None}
        object_last_task = {}

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)
            self.tasks[i] = {"agent": agent, "action": action, "object": obj}

            if obj and obj in object_last_task:
                self.edges.append((object_last_task[obj], i))

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
        action = action.lower()
        if "pick " in action:
            return action.split("pick ")[1].strip()
        elif "move " in action:
            return action.split("move ")[1].split(" to ")[0].strip()
        elif "place " in action:
            # Xử lý cả "in" và "into"
            if " into " in action:
                return action.split("place ")[1].split(" into ")[0].strip()
            elif " in " in action:
                return action.split("place ")[1].split(" in ")[0].strip()
            elif " on " in action:
                return action.split("place ")[1].split(" on ")[0].strip()
            else:
                return action.split("place ")[1].strip()
        return ""

    def assign_waves(self):
        subtasks = self._find_object_based_subtasks()

        wave = 1
        pending_subtasks = []

        for subtask in subtasks:

            has_transfer = any(self.tasks[task_id]["agent"] in ["robottohuman", "humantorobot"]
                               for task_id in subtask)

            if has_transfer:
                for pending_subtask in pending_subtasks:
                    for task_id in pending_subtask:
                        self.tasks[task_id]["wave"] = wave

                if pending_subtasks:
                    wave += 1

                pending_subtasks = []

                for task_id in subtask:
                    self.tasks[task_id]["wave"] = wave

                wave += 1
            else:

                pending_subtasks.append(subtask)

        for pending_subtask in pending_subtasks:
            for task_id in pending_subtask:
                self.tasks[task_id]["wave"] = wave


        if not any(self.tasks[t].get("wave") for t in self.tasks):
            for task_id in self.tasks:
                self.tasks[task_id]["wave"] = 1

    def _find_object_based_subtasks(self):
        subtasks = []
        current_subtask = []
        current_object = None

        for task_id in sorted(self.tasks.keys()):
            task_object = self.tasks[task_id]["object"]

            if current_object is None:
                # Task đầu tiên
                current_object = task_object
                current_subtask = [task_id]
            elif task_object == current_object:
                current_subtask.append(task_id)
            else:
                if current_subtask:
                    subtasks.append(current_subtask)
                current_object = task_object
                current_subtask = [task_id]

        if current_subtask:
            subtasks.append(current_subtask)

        return subtasks

    def export_json(self, filename="commands.json"):
        self.assign_waves()

        commands = []
        for task_id in sorted(self.tasks.keys()):
            task = self.tasks[task_id]
            agent = task["agent"]

            if agent == "robottohuman":
                agent = "robot"
                lane = "transfer"
            elif agent == "humantorobot":
                agent = "human"
                lane = "transfer"
            else:
                lane = agent
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
        action = action.lower()

        if action.startswith("pick "):
            return "pick", action[5:], ""
        elif action.startswith("place "):
            # Xử lý cả "in" và "into"
            if " into " in action:
                parts = action[6:].split(" into ")
            elif " in " in action:
                parts = action[6:].split(" in ")
            elif "on" in action:
                parts = action[6:].split(" on ")
            else:
                parts = [action[6:], ""]
            return "place", parts[0], parts[1] if len(parts) > 1 else ""
        elif action.startswith("move "):
            parts = action[5:].split(" to ")
            return "move", parts[0], parts[1] if len(parts) > 1 else ""

        return "unknown", action, ""

    def print_summary(self):
        """In ra tóm tắt các wave và task"""
        self.assign_waves()

        print("\n=== TASK SUMMARY ===")
        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]
            has_transfer = any(task["agent"] in ["robottohuman", "humantorobot"]
                               for _, task in tasks)
            execution_type = "Sequential" if has_transfer else "Parallel"

            print(f"\nWave {wave_id} ({execution_type}):")
            for task_id, task in sorted(tasks):
                lane = "transfer" if task["agent"] in ["robottohuman", "humantorobot"] else task["agent"]
                print(f"  Task {task_id}: {task['agent']} - {task['action']} (lane: {lane})")



# Hàm thực thi file JSON
def run_from_json(json_file, robot_ids, object_map):
    """Static method để chạy từ JSON file"""
    with open(json_file) as f:
        commands = json.load(f)

    waves = defaultdict(list)
    for cmd in commands:
        waves[cmd["wave"]].append(cmd)

    for wave_id in sorted(waves.keys()):
        tasks = waves[wave_id]
        has_transfer = any(t["lane"] == "transfer" for t in tasks)

        if has_transfer:
            print(f"Wave {wave_id}: Sequential execution")
            _execute_sequential(tasks, robot_ids, object_map)
        else:
            print(f"Wave {wave_id}: Parallel execution")
            _execute_parallel(tasks, robot_ids, object_map)



def _execute_sequential(tasks, robot_ids, object_map):
    """Execute tasks sequentially"""
    constraint = None
    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, constraint)



def _execute_parallel(tasks, robot_ids, object_map):
    """Execute tasks in parallel by agent"""
    agent_tasks = defaultdict(list)
    for task in tasks:
        agent_tasks[task["agent"]].append(task)

    threads = []
    for agent, task_list in agent_tasks.items():
        thread = threading.Thread(target=_execute_agent_tasks,
                                  args=(agent, task_list, robot_ids, object_map))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def _execute_agent_tasks(agent, tasks, robot_ids, object_map):
    """Execute tasks for a specific agent"""
    constraint = None
    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, constraint)


def _execute_task(task, robot_ids, object_map, constraint):
    agent = task["agent"]
    action = task["action"]
    obj = task["object"]
    dest = task["destination"]

    if agent not in robot_ids:
        print(f"Unknown agent: {agent}")
        return constraint

    robot_id = robot_ids[agent]

    try:
        print(f"Executing: {agent} {action} {obj} {dest}")

        if action == "pick" and obj in object_map:
            pos = robot_action.get_position(object_map[obj])
            return robot_action.pick(robot_id, object_map[obj], pos)


        elif action == "place":

            if dest in object_map:

                pos = robot_action.get_position(object_map[dest])

            else:

                pos = robot_action.get_position(object_map.get(obj, obj))

            robot_action.place(agent, pos, constraint, robot_ids)

            return None

        elif action == "move":
            target_pos = [0.33, -0.2, 0.65] if dest == "robot" else [0.7, 0.2, 0.65]
            robot_action.move_to_target(robot_id, target_pos, constraint)
            if constraint:
                robot_action.place(agent, target_pos, constraint, robot_ids)
                return None

    except Exception as e:
        print(f"Error executing {action} for {agent}: {e}")

    return constraint

processor = TaskProcessor(task_plan_2)
processor.print_summary()
processor.export_json("commands_task2.json")

