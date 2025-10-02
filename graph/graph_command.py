from collections import defaultdict
import json
import re
from AI_module.LLM import call_gemini

task_plan = [("robot1", "pick green_cube_2"),
("robot1", "place green_cube_2 into green_bowl"),
("robot2", "pick yellow_cube"),
("robot2", "place yellow_cube into yellow_bowl"),
("robot1", "pick red_cube"),
("robot1torobot2", "move red_cube to robot2"),
("robot2", "pick red_cube"),
("robot2", "place red_cube into red_bowl"),
("robot2", "pick green_cube_1"),
("robot2torobot1", "move green_cube_1 to robot1"),
("robot1", "pick green_cube_1"),
("robot1", "place green_cube_1 into green_bowl"),]


class TaskProcessor:
    def __init__(self, task_plan):
        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self.robots = set()
        self.handoff_agents = set()
        self._discover_agents()
        self._process_tasks()

    def _discover_agents(self):
        """Tự động phát hiện các robot và handoff agents từ task plan"""
        handoff_pattern = re.compile(r'^(robot\d+)to(robot\d+)$')

        for agent, _ in self.task_plan:
            match = handoff_pattern.match(agent)
            if match:
                # Đây là handoff agent (vd: robot1torobot2)
                self.handoff_agents.add(agent)
                # Thêm cả 2 robot vào set
                self.robots.add(match.group(1))
                self.robots.add(match.group(2))
            elif agent.startswith('robot'):
                # Đây là robot thông thường
                self.robots.add(agent)

        print(f"Detected robots: {sorted(self.robots)}")
        print(f"Detected handoff agents: {sorted(self.handoff_agents)}")

    def _get_handoff_target(self, handoff_agent):
        match = re.match(r'^robot\d+to(robot\d+)$', handoff_agent)
        return match.group(1) if match else None

    def _get_handoff_source(self, handoff_agent):
        match = re.match(r'^(robot\d+)torobot\d+$', handoff_agent)
        return match.group(1) if match else None

    def _process_tasks(self):
        # Khởi tạo handoffs dict động cho tất cả handoff agents
        handoffs = {agent: None for agent in self.handoff_agents}
        object_last_task = {}  # key: "agent_object"

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)
            self.tasks[i] = {"agent": agent, "action": action, "object": obj}

            # Xử lý dependency dựa trên agent + object
            if obj and agent not in self.handoff_agents:
                agent_object_key = f"{agent}_{obj}"

                if agent_object_key in object_last_task:
                    self.edges.append((object_last_task[agent_object_key], i))

                object_last_task[agent_object_key] = i

            # Xử lý handoff logic
            if agent in handoffs:
                # Đây là task handoff, lưu lại
                handoffs[agent] = i
            else:
                # Kiểm tra xem có handoff nào đang chờ robot này không
                for handoff_agent, handoff_task_id in handoffs.items():
                    if handoff_task_id is not None:
                        target_robot = self._get_handoff_target(handoff_agent)
                        if agent == target_robot:
                            # Tạo edge từ handoff task đến task hiện tại
                            self.edges.append((handoff_task_id, i))
                            # Reset handoff
                            handoffs[handoff_agent] = None

    def _extract_object(self, action):
        """Extract the object from the action string"""
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

    def assign_waves(self):
        """Assign waves to tasks based on the transfer actions"""
        subtasks = self._find_object_based_subtasks()
        wave = 1
        pending_subtasks = []

        for subtask in subtasks:
            has_transfer = any(self.tasks[task_id]["agent"] in self.handoff_agents
                               for task_id in subtask)

            if has_transfer:
                # Flush pending subtasks trước
                for pending_subtask in pending_subtasks:
                    for task_id in pending_subtask:
                        self.tasks[task_id]["wave"] = wave

                if pending_subtasks:
                    wave += 1
                pending_subtasks = []

                # Assign wave cho subtask có transfer
                for task_id in subtask:
                    self.tasks[task_id]["wave"] = wave
                wave += 1
            else:
                pending_subtasks.append(subtask)

        # Assign wave cho các pending subtasks còn lại
        for pending_subtask in pending_subtasks:
            for task_id in pending_subtask:
                self.tasks[task_id]["wave"] = wave

        # Fallback: nếu không có wave nào được assign
        if not any(self.tasks[t].get("wave") for t in self.tasks):
            for task_id in self.tasks:
                self.tasks[task_id]["wave"] = 1

    def _find_object_based_subtasks(self):
        """Find subtasks based on the objects involved in the tasks"""
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

    def _get_wave_format(self):
        """Get wave format (parallel1, sequential1, etc.)"""
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
            has_transfer = any(task["agent"] in self.handoff_agents
                               for _, task in tasks)

            if has_transfer:
                sequential_count += 1
                wave_formats[wave_id] = f"sequential{sequential_count}"
            else:
                parallel_count += 1
                wave_formats[wave_id] = f"parallel{parallel_count}"

        return wave_formats

    def export_json(self, filename="commands_task1.json"):
        """Export the tasks to a JSON file with the required format"""
        self.assign_waves()
        wave_formats = self._get_wave_format()

        commands = []
        for task_id in sorted(self.tasks.keys()):
            task = self.tasks[task_id]
            agent = task["agent"]

            # Xử lý lane và agent cho handoff agents
            if agent in self.handoff_agents:
                # Lấy robot nguồn làm agent, lane là transfer
                agent = self._get_handoff_source(agent)
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
        print(f"✅ Exported to {filename}")

    def parse_action(self, action):
        """Parse the action string to extract the verb, object, and destination"""
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
        """Print a summary of tasks organized by waves"""
        self.assign_waves()
        wave_formats = self._get_wave_format()

        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]
            has_transfer = any(task["agent"] in self.handoff_agents
                               for _, task in tasks)
            execution_type = "Sequential" if has_transfer else "Parallel"
            wave_format = wave_formats.get(wave_id, "parallel1")

            print(f"\n🌊 Wave {wave_id} ({execution_type}) - Format: {wave_format}:")
            for task_id, task in sorted(tasks):
                lane = "transfer" if task["agent"] in self.handoff_agents else task["agent"]
                print(f"  └─ Task {task_id}: {task['agent']} - {task['action']} (lane: {lane})")


if __name__ == "__main__":
    task_processor = TaskProcessor(task_plan)
    task_processor.print_summary()
    task_processor.export_json("commands_task1.json")