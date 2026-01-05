"""
Task Processor Module
Processes LLM output into structured task graph for robot execution.
"""

from collections import defaultdict, deque
import json
import re
from AI_module.call_gemini_test_truth import call_gemini_4, call_gemini_1, call_gemini_2, call_gemini_3, call_gemini_5  # Groundtruth
from AI_module.LLM import call_gemini  # Call real LLM


class TaskProcessor:
    """
    Processes task plans from LLM into executable JSON format.
    
    Handles:
    - Parsing agent and action information
    - Building task dependency graph
    - Identifying handoff operations between robots
    - Exporting to JSON for RobotExecutor
    """
    
    def __init__(self, task_plan):
        """
        Initialize processor with task plan from LLM.
        
        Args:
            task_plan: List of tuples [(agent, action, dependencies), ...]
        """
        if not task_plan:
            raise ValueError("task_plan cannot be empty")

        self.task_plan = task_plan
        self.tasks = {}           # Task ID -> task details
        self.edges = []           # Dependency edges [(from_id, to_id), ...]
        self.robots = set()       # Set of robot agents
        self.handoff_agents = set()  # Set of handoff operations (e.g., "robot1torobot2")

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
        Process task plan and build task graph with dependencies.
        Creates tasks dict and dependency edges from LLM output.
        """
        for i, (agent, action, dependencies) in enumerate(self.task_plan, start=1):
            obj = self._extract_object(action)

            # Store task details with dependency string for JSON export
            self.tasks[i] = {
                "agent": agent,
                "action": action,
                "object": obj,
                "dependencies": dependencies  # Original dependency string from LLM
            }

            # Build dependency edges from LLM dependency format
            dep_nodes = self._parse_dependencies(dependencies)
            for dep_node in dep_nodes:
                self.edges.append((dep_node, i))  # Edge: dep_node -> current task

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

    def parse_action(self, action):
        action = action.lower().strip()

        if action.startswith("pick "):
            return "pick", action[5:].strip(), ""

        elif action.startswith("place "):
            # Split based on common prepositions
            if " into " in action:
                parts = action[6:].split(" into ", 1)
            elif " in " in action:
                parts = action[6:].split(" in ", 1)
            elif " on " in action:
                parts = action[6:].split(" on ", 1)
            elif " onto " in action:
                parts = action[6:].split(" onto ", 1)
            else:
                parts = [action[6:], ""]

            obj = parts[0].strip()
            raw_dest = parts[1].strip() if len(parts) > 1 else ""
            dest = raw_dest.split()[-1] if raw_dest else ""

            return "place", obj, dest

        elif action.startswith("move "):
            parts = action[5:].split(" to ", 1)
            obj = parts[0].strip()
            raw_dest = parts[1].strip() if len(parts) > 1 else ""
            dest = raw_dest.split()[-1] if raw_dest else ""

            return "move", obj, dest

        elif action.startswith("sweep "):
            obj = action[6:].strip() if len(action) > 6 else ""
            return "sweep", obj, ""

        return "unknown", action, ""

    def export_json(self, filename="commands_task1.json"):
        """
        Export processed tasks to JSON file for RobotExecutor.
        
        Output format:
        {
            "id": task_id,
            "agent": robot name,
            "action": pick/place/move/sweep,
            "object": target object,
            "destination": target location,
            "lane": execution lane,
            "node": dependency string
        }
        
        Args:
            filename: Output JSON filename
        """
        commands = []
        for task_id in sorted(self.tasks.keys()):
            task = self.tasks[task_id]
            agent = task["agent"]

            # Handle handoff operations (e.g., "robot1torobot2")
            if agent in self.handoff_agents:
                source_agent = self._get_handoff_source(agent)
                dest_agent = self._get_handoff_target(agent)
                lane = "transfer"
            else:
                source_agent = agent
                dest_agent = ""
                lane = agent

            # Parse action string into verb, object, destination
            verb, obj, dest = self.parse_action(task["action"])

            # For move action during handoff, destination is the receiving robot
            if verb == "move" and agent in self.handoff_agents:
                dest = dest_agent

            commands.append({
                "id": task_id,
                "agent": source_agent,
                "action": verb,
                "object": obj.replace(" ", "_") if obj else "",
                "destination": dest.replace(" ", "_") if dest else "",
                "lane": lane,
                "node": task["dependencies"]  # Dependency string for executor
            })

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(commands, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(commands)} commands to {filename}")


if __name__ == "__main__":
    task_plan = call_gemini() #Define which function to call for groundtruth or LLM
    processor = TaskProcessor(task_plan)
    processor.export_json("commands_task_4.json")