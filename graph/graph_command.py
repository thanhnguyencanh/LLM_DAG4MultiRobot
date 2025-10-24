from collections import defaultdict, deque
import json
import re
from AI_module.call_gemini_test import call_gemini_1


#task_plan = call_gemini()
class TaskProcessor:
    def __init__(self, task_plan):
        if not task_plan:
            raise ValueError("task_plan cannot be empty")

        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self.robots = set()
        self.handoff_agents = set()

        self._discover_agents()
        self._process_tasks()

    def _discover_agents(self):
        handoff_pattern = re.compile(r'^(robot\d+)to(robot\d+)$')

        for agent, _, _ in self.task_plan:
            match = handoff_pattern.match(agent)
            if match:
                self.handoff_agents.add(agent)
                self.robots.add(match.group(1))
                self.robots.add(match.group(2))
            elif agent.startswith('robot'):
                self.robots.add(agent)

    def _get_handoff_target(self, handoff_agent):
        match = re.match(r'^robot\d+to(robot\d+)$', handoff_agent)
        return match.group(1) if match else None

    def _get_handoff_source(self, handoff_agent):
        match = re.match(r'^(robot\d+)torobot\d+$', handoff_agent)
        return match.group(1) if match else None

    def _parse_dependencies(self, dep_str):
        """
        Parse dependency string like 'node[1]', 'node[3,6]', or 'node[]'
        Returns: list of node IDs
        """
        if not dep_str or dep_str == "node[]":
            return []

        # Extract numbers from node[...]
        match = re.search(r'node\[([\d,\s]+)\]', dep_str)
        if match:
            nums_str = match.group(1)
            return [int(x.strip()) for x in nums_str.split(',') if x.strip()]
        return []

    def _process_tasks(self):
        """
        Tạo tasks và edges dựa trên dependencies từ LLM
        """
        for i, (agent, action, dependencies) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)

            self.tasks[i] = {
                "agent": agent,
                "action": action,
                "object": obj
            }

            # Tạo edges từ dependencies của LLM
            dep_nodes = self._parse_dependencies(dependencies)
            for dep_node in dep_nodes:
                self.edges.append((dep_node, i))

            print(f"Task {i}: {agent} | {action} | deps: {dep_nodes}")

    def _extract_object(self, action):
        action = action.lower().strip()

        if action.startswith("pick "):
            return action.split("pick ")[1].strip()

        elif action.startswith("move "):
            return action.split("move ")[1].split(" to ")[0].strip()

        elif action.startswith("place "):
            if " into " in action:
                return action.split("place ")[1].split(" into ")[0].strip()
            elif " in " in action:
                return action.split("place ")[1].split(" in ")[0].strip()
            elif " on " in action:
                return action.split("place ")[1].split(" on ")[0].strip()
            else:
                return action.split("place ")[1].strip()

        elif action.startswith("sweep "):
            return action[6:].strip() if len(action) > 6 else ""

        return ""

    def assign_waves(self):
        """
        Gán wave: Chỉ những nodes có dependency trực tiếp với nhau mới cùng wave
        Waves được sort theo node đầu tiên (nhỏ nhất) của mỗi wave
        """
        all_nodes = set(self.tasks.keys())

        # Build predecessor map
        predecessors = defaultdict(set)
        for u, v in self.edges:
            predecessors[v].add(u)

        # Build successor map
        successors = defaultdict(set)
        for u, v in self.edges:
            successors[u].add(v)

        print("\n🔍 Dependency Analysis:")
        for node in sorted(all_nodes):
            deps = sorted(predecessors[node])
            print(f"  Node {node}: deps={deps}")

        print("\n📊 Initial Wave Grouping:")

        remaining = sorted(all_nodes)
        temp_waves = []  # Lưu tạm các wave groups

        while remaining:
            # Bắt đầu wave mới với node đầu tiên trong remaining
            current_wave = [remaining[0]]
            to_remove = [remaining[0]]

            # Thử thêm các nodes còn lại nếu có dependency với nodes trong current_wave
            for node_id in remaining[1:]:
                has_connection = False

                # Kiểm tra xem node này có dependency với bất kỳ node nào trong current_wave không
                for wave_node in current_wave:
                    # Có edge từ wave_node đến node_id (predecessor)
                    if wave_node in predecessors[node_id]:
                        has_connection = True
                        break
                    # Có edge từ node_id đến wave_node (successor)
                    if wave_node in successors[node_id]:
                        has_connection = True
                        break

                if has_connection:
                    current_wave.append(node_id)
                    to_remove.append(node_id)

            temp_waves.append(sorted(current_wave))
            print(f"  Group {len(temp_waves)}: {sorted(current_wave)}")

            # Loại bỏ các nodes đã xử lý
            remaining = [n for n in remaining if n not in to_remove]

        # Sort waves theo node nhỏ nhất trong mỗi wave
        temp_waves.sort(key=lambda wave: min(wave))

        print(f"\n📊 Sorted Wave Assignment:")

        # Gán wave numbers sau khi sort
        for wave_num, wave_nodes in enumerate(temp_waves, start=1):
            for node in wave_nodes:
                self.tasks[node]["wave"] = wave_num
            print(f"  Wave {wave_num}: {wave_nodes}")

        print(f"\n✅ Assigned {len(temp_waves)} waves to {len(self.tasks)} tasks")

    def parse_action(self, action):
        action = action.lower().strip()

        if action.startswith("pick "):
            return "pick", action[5:].strip(), ""

        elif action.startswith("place "):
            if " into " in action:
                parts = action[6:].split(" into ", 1)
            elif " in " in action:
                parts = action[6:].split(" in ", 1)
            elif " on " in action:
                parts = action[6:].split(" on ", 1)
            else:
                parts = [action[6:], ""]
            obj = parts[0].strip()
            dest = parts[1].strip() if len(parts) > 1 else ""
            return "place", obj, dest

        elif action.startswith("move "):
            parts = action[5:].split(" to ", 1)
            obj = parts[0].strip()
            dest = parts[1].strip() if len(parts) > 1 else ""
            return "move", obj, dest

        elif action.startswith("sweep "):
            obj = action[6:].strip() if len(action) > 6 else ""
            return "sweep", obj, ""

        return "unknown", action, ""

    def export_json(self, filename="commands_task1.json"):
        self.assign_waves()
        commands = []
        for task_id in sorted(self.tasks.keys()):
            task = self.tasks[task_id]
            agent = task["agent"]
            if agent in self.handoff_agents:
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
                "wave": task.get("wave", 1)
            })

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(commands, f, indent=2, ensure_ascii=False)

        print(f"✅ Exported {len(commands)} commands to {filename}")

    def print_summary(self):
        self.assign_waves()

        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        print("\n" + "=" * 70)
        print("TASK EXECUTION PLAN (Wave-based Scheduling)")
        print("=" * 70)

        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]

            # Determine if wave has handoff (sequential) or not (parallel)
            has_transfer = any(task["agent"] in self.handoff_agents
                               for _, task in tasks)
            execution_type = "Sequential" if has_transfer else "Parallel"

            print(f"\nWave {wave_id} ({execution_type}) - {len(tasks)} task(s):")

            for task_id, task in sorted(tasks):
                lane = "transfer" if task["agent"] in self.handoff_agents else task["agent"]
                obj = f"[{task['object']}]" if task['object'] else ""
                print(f"  Task {task_id:2d}: [{task['agent']:15s}] {task['action']:30s} {obj:15s} (lane: {lane})")

        print(f"\n📊 Summary: {len(waves)} waves, {len(self.tasks)} total tasks")


if __name__ == "__main__":
    task_plan = call_gemini_1()
    processor = TaskProcessor(task_plan)
    processor.print_summary()
    processor.export_json("commands_task1.json")