from collections import defaultdict, deque
import json
import re

def call_gemini():
    return [
        ("robot2", "pick yellow_cube"),
        ("robot2", "place yellow_cube into yellow_bowl"),
        ("robot1", "pick green_cube_2"),
        ("robot1", "place green_cube_2 into green_bowl"),
        ("robot2", "pick green_cube_1"),
        ("robot2torobot1", "move green_cube_1 to robot1"),
        ("robot1", "pick green_cube_1"),
        ("robot1", "place green_cube_1 into green_bowl"),
        ("robot1", "pick red_cube"),
        ("robot1torobot2", "move red_cube to robot2"),
        ("robot2", "pick red_cube"),
        ("robot2", "place red_cube into red_bowl")
    ]


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

        for agent, _ in self.task_plan:
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

    def _process_tasks(self):
        handoffs = {agent: None for agent in self.handoff_agents}
        object_last_task = {}  # Dictionary to track LastTask[o] as in paper

        for i, (agent, action) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)
            self.tasks[i] = {
                "agent": agent,
                "action": action,
                "object": obj
            }

            # Create edges based on object dependencies (as described in paper)
            # "If LastTask[o] exists, add edge (v_j, v_i) where v_j = LastTask[o]"
            if obj:
                if obj in object_last_task:
                    self.edges.append((object_last_task[obj], i))
                object_last_task[obj] = i  # Update LastTask[o] ← v_i

            # Handle handoff logic (collaboration lane)
            if agent in self.handoff_agents:
                handoffs[agent] = i
            else:
                # Check if this task follows any pending handoff
                for handoff_agent, handoff_task_id in list(handoffs.items()):
                    if handoff_task_id is not None:
                        target_robot = self._get_handoff_target(handoff_agent)
                        if agent == target_robot:
                            # Create edge from handoff to target robot's next task
                            self.edges.append((handoff_task_id, i))
                            handoffs[handoff_agent] = None

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
        all_nodes = set(self.tasks.keys())
        adj = defaultdict(list)
        for u, v in self.edges:
            adj[u].append(v)

        visited = set()
        wave = 1

        # Get sorted list of node IDs
        sorted_nodes = sorted(all_nodes)

        while visited != all_nodes:
            seed = None
            for node_id in sorted_nodes:
                if node_id not in visited:
                    seed = node_id
                    break

            if seed is None:
                break

            # BFS/DFS to traverse all connected edges from seed
            # Append all reachable nodes to current wave
            queue = deque([seed])
            current_wave_nodes = []

            while queue:
                node = queue.popleft()

                if node in visited:
                    continue

                visited.add(node)
                current_wave_nodes.append(node)

                # Traverse all outgoing edges (adjacent nodes)
                for neighbor in adj[node]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            # Assign wave to all nodes in current group
            for node in current_wave_nodes:
                self.tasks[node]["wave"] = wave

            print(f"  Wave {wave}: {sorted(current_wave_nodes)}")
            wave += 1

        print(f"📊 Assigned {wave - 1} waves to {len(self.tasks)} tasks")

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
        """
        Print a detailed summary of tasks organized by waves
        Shows execution plan with parallel/sequential indicators
        """
        self.assign_waves()

        waves = defaultdict(list)
        for task_id, task in self.tasks.items():
            waves[task.get("wave", 1)].append((task_id, task))

        print("\n" + "=" * 70)
        print("📋 TASK EXECUTION PLAN (Wave-based Scheduling)")
        print("=" * 70)

        for wave_id in sorted(waves.keys()):
            tasks = waves[wave_id]

            # Determine if wave has handoff (sequential) or not (parallel)
            has_transfer = any(task["agent"] in self.handoff_agents
                               for _, task in tasks)
            execution_type = "Sequential" if has_transfer else "Parallel"

            print(f"\n📦 Wave {wave_id} ({execution_type}) - {len(tasks)} task(s):")

            for task_id, task in sorted(tasks):
                lane = "transfer" if task["agent"] in self.handoff_agents else task["agent"]
                obj = f"[{task['object']}]" if task['object'] else ""
                print(f"  └─ Task {task_id:2d}: [{task['agent']:15s}] {task['action']:30s} {obj:15s} (lane: {lane})")

        print("\n" + "=" * 70)
        print(f"📊 Summary: {len(waves)} waves, {len(self.tasks)} total tasks")
        print(f"🤖 Robots: {', '.join(sorted(self.robots))}")
        print("=" * 70 + "\n")

if __name__ == "__main__":
    task_plan = call_gemini()
    processor = TaskProcessor(task_plan)
    processor.print_summary()
    processor.export_json("commands_task1.json")
