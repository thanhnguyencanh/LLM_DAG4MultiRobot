from collections import defaultdict
import json

task_plan = [("robot", "pick yellow_cube"),
             ("human", "pick green_cube_2"),
             ("robot", "place yellow_cube into yellow_bowl"),
             ("human", "place green_cube_2 into green_bowl"),
             ("human", "pick red_cube"),
             ("humantorobot", "move red_cube to robot"),
             ("robot", "pick red_cube"),
             ("robot", "place red_cube into red_bowl"),
             ("robot", "pick green_cube_1"),
             ("robottohuman", "move green_cube_1 to human"),
             ("human", "pick green_cube_1"),
             ("human", "place green_cube_1 into green_bowl"), ]


class TaskProcessor:
    def __init__(self, task_plan):
        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self._process_tasks()

    def _process_tasks(self):
        handoffs = {"robottohuman": None, "humantorobot": None}
        object_last_task = {}  # key: "agent_object"

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)
            self.tasks[i] = {"agent": agent, "action": action, "object": obj}

            # Xử lý dependency dựa trên agent + object
            if obj and agent not in ["robottohuman", "humantorobot"]:
                agent_object_key = f"{agent}_{obj}"

                if agent_object_key in object_last_task:
                    self.edges.append((object_last_task[agent_object_key], i))

                object_last_task[agent_object_key] = i

            if agent in handoffs:
                handoffs[agent] = i
            elif agent == "human" and handoffs["robottohuman"]:
                self.edges.append((handoffs["robottohuman"], i))
                handoffs["robottohuman"] = None
            elif agent == "robot" and handoffs["humantorobot"]:
                self.edges.append((handoffs["humantorobot"], i))
                handoffs["humantorobot"] = None

    # Extract the object from the action string (rule-based) but can improve with NLP
    def _extract_object(self, action):
        action = action.lower()
        if "pick " in action:
            return action.split("pick ")[1].strip()

        elif "move " in action:
            return action.split("move ")[1].split(" to ")[0].strip()

        elif "place " in action:
            if " into " in action:
                return action.split("place ")[1].split(" into ")[0].strip()
            elif " in " in action:
                return action.split("place ")[1].split(" in ")[0].strip()
            elif " on " in action:
                return action.split("place ")[1].split(" on ")[0].strip()
            else:
                return action.split("place ")[1].strip()
        return ""

    # Assign waves to tasks based on the transfer actions ( parralel or sequential execution )
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

    # Find subtasks based on the objects involved in the tasks
    def _find_object_based_subtasks(self):
        subtasks = []
        current_subtask = []
        current_object = None

        for task_id in sorted(self.tasks.keys()):
            task_object = self.tasks[task_id]["object"]

            if current_object is None:
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

    # Get wave format (parallel1, sequential1, etc.)
    def _get_wave_format(self):
        wave_formats = {}
        parallel_count = 0
        sequential_count = 0

        # Group tasks by wave
        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        # Determine format for each wave
        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]
            has_transfer = any(task["agent"] in ["robottohuman", "humantorobot"]
                               for _, task in tasks)

            if has_transfer:
                sequential_count += 1
                wave_formats[wave_id] = f"sequential{sequential_count}"
            else:
                parallel_count += 1
                wave_formats[wave_id] = f"parallel{parallel_count}"

        return wave_formats

    # Export the tasks to a JSON file with the required format
    def export_json(self, filename="commands_task1.json"):
        self.assign_waves()
        wave_formats = self._get_wave_format()

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
            verb, obj, dest = self.parse_action(task["action"])

            commands.append({
                "id": task_id,
                "agent": agent,
                "action": verb,
                "object": obj.replace(" ", "_") if obj else "",
                "destination": dest.replace(" ", "_") if dest else "",
                "lane": lane,
                "wave": wave_formats.get(task.get("wave", 1), "parallel1")
            })

        with open(filename, "w") as f:
            json.dump(commands, f, indent=2)
        print(f"Exported to {filename}")

    # Parse the action string to extract the verb, object, and destination
    def parse_action(self, action):
        action = action.lower()

        if action.startswith("pick "):
            return "pick", action[5:], ""
        elif action.startswith("place "):
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
        elif action.startswith("sweep "):
            obj = action[6:] if len(action) > 6 else ""
            return "sweep", obj, ""
        return "unknown", action, ""

    def print_summary(self):
        self.assign_waves()
        wave_formats = self._get_wave_format()

        print("\n TASK SUMMARY")
        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]
            has_transfer = any(task["agent"] in ["robottohuman", "humantorobot"]
                               for _, task in tasks)
            execution_type = "Sequential" if has_transfer else "Parallel"
            wave_format = wave_formats.get(wave_id, "parallel1")

            print(f"\nWave {wave_id} ({execution_type}) - Format: {wave_format}:")
            for task_id, task in sorted(tasks):
                lane = "transfer" if task["agent"] in ["robottohuman", "humantorobot"] else task["agent"]
                print(f"  Task {task_id}: {task['agent']} - {task['action']} (lane: {lane})")


task_processor = TaskProcessor(task_plan)
task_processor.print_summary()
task_processor.export_json("commands_task1.json")