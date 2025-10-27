import threading
from collections import defaultdict
import json
import time
from robot import robot_action
from Task3.environment import Environment # Chỉnh lại trước khi chạy task nào đó


class RobotExecutor:
    def __init__(self, robot_ids, object_map, transfer_positions=None):
        self.robot_ids = robot_ids
        self.object_map = object_map

        # Agent state management
        self.agent_states = {agent: "free" for agent in robot_ids.keys()}
        self.state_lock = threading.Lock()

        # Task completion tracking
        self.completed_tasks = set()
        self.completion_lock = threading.Lock()

        # Constraint tracking
        self.task_constraints = {}
        self.constraint_lock = threading.Lock()

        # Global task pool
        self.available_tasks = []
        self.task_pool_lock = threading.Lock()

        if transfer_positions is None:
            env = Environment()
            self.transfer_positions = self._get_transfer_positions_from_env(env)
        else:
            self.transfer_positions = transfer_positions

        self._validate_robots()

    def _get_transfer_positions_from_env(self, env):
        if not hasattr(env, 'handoff_points') or not env.handoff_points:
            raise ValueError(
                "[ERROR] Environment does not have 'handoff_points'. "
                "Please define handoff_points in Environment"
            )
        transfer_pos = env.handoff_points
        print("[INFO] Handoff points loaded from Environment:")
        for key, pos in sorted(transfer_pos.items()):
            print(f"  {key}: {pos}")
        return transfer_pos

    def _validate_robots(self):
        if not self.transfer_positions:
            raise ValueError(
                "[ERROR] No handoff points available. "
                "Please define handoff_points in Environment"
            )

    def get_transfer_position(self, position_key):
        if position_key in self.transfer_positions:
            return self.transfer_positions[position_key]
        else:
            raise KeyError(
                f"[ERROR] Transfer position '{position_key}' not found. "
                f"Available: {list(self.transfer_positions.keys())}"
            )

    def print_transfer_positions(self):
        print("\n" + "=" * 60)
        print(" HANDOFF POINTS (for move action)")
        print("=" * 60)
        for key, pos in sorted(self.transfer_positions.items()):
            print(f"{key}: {pos}")
        print("=" * 60 + "\n")

    def set_agent_busy(self, agent):
        with self.state_lock:
            self.agent_states[agent] = "busy"
            print(f"  [{agent}] → BUSY")

    def set_agent_free(self, agent):
        with self.state_lock:
            self.agent_states[agent] = "free"
            print(f"  [{agent}] → FREE")

    def is_agent_free(self, agent):
        with self.state_lock:
            return self.agent_states[agent] == "free"

    def mark_task_completed(self, task_id):
        with self.completion_lock:
            self.completed_tasks.add(task_id)
            print(f"  [Task {task_id}] ✓ Completed")

    def is_task_completed(self, task_id):
        with self.completion_lock:
            return task_id in self.completed_tasks

    def set_task_constraint(self, task_id, constraint):
        with self.constraint_lock:
            self.task_constraints[task_id] = constraint

    def get_task_constraint(self, task_id):
        with self.constraint_lock:
            return self.task_constraints.get(task_id)

    def run_from_json(self, json_file):
        with open(json_file) as f:
            commands = json.load(f)

        self.task_map = {cmd["id"]: cmd for cmd in commands}
        self.dependency_map = self._build_dependency_map(commands)

        print("\n" + "=" * 70)
        print("EXECUTION PLAN - DEPENDENCY-BASED PARALLEL EXECUTION")
        print("=" * 70)
        print(f"Total tasks: {len(commands)}")
        print(f"Agents: {list(self.robot_ids.keys())}")
        print("=" * 70 + "\n")

        # Populate task pool
        with self.task_pool_lock:
            self.available_tasks = commands.copy()

        print(f"[Task Pool] {len(self.available_tasks)} tasks loaded\n")

        # Start worker thread for each agent
        threads = []
        for agent in self.robot_ids.keys():
            t = threading.Thread(target=self._agent_worker, args=(agent,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        print("\n✅ All tasks completed!")

    def _build_dependency_map(self, commands):
        """Build dependency map from explicit node dependencies in JSON"""
        dependency_map = defaultdict(list)

        for cmd in commands:
            task_id = cmd["id"]

            # Parse node dependencies from command
            # Expected format: "node[1,2,3]" or "node[]"
            node_str = cmd.get("node", "node[]")

            # Extract dependency IDs from node string
            if "node[" in node_str:
                # Extract content between [ and ]
                start = node_str.index("[") + 1
                end = node_str.index("]")
                deps_str = node_str[start:end].strip()

                if deps_str:  # If not empty
                    # Split by comma and convert to integers
                    dep_ids = [int(d.strip()) for d in deps_str.split(",")]
                    dependency_map[task_id] = dep_ids

        print("\n[Dependency Map]")
        if dependency_map:
            for task_id in sorted(dependency_map.keys()):
                deps = dependency_map[task_id]
                print(f"  Task {task_id} depends on: {deps}")
        else:
            print("  No dependencies found")
        print()

        return dependency_map

    def _agent_worker(self, agent):
        """
        Worker thread for each agent.
        Agent picks up any available task assigned to it when free.
        """
        print(f"\n[{agent}] Worker started")

        while True:
            # Try to get next available task for this agent
            task = self._get_next_available_task(agent)

            if task is None:
                # No more tasks available
                if self._all_tasks_completed():
                    print(f"[{agent}] No more tasks, shutting down")
                    break
                else:
                    # Wait a bit for dependencies to clear
                    time.sleep(0.1)
                    continue

            task_id = task["id"]

            # Wait for dependencies
            self._wait_for_dependencies(task_id)

            # Get constraint if needed
            prev_constraint = None
            if task["action"] in ["place", "move"]:
                for prev_task in self.task_map.values():
                    if (prev_task["agent"] == agent and
                            prev_task["object"] == task["object"] and
                            prev_task["action"] == "pick" and
                            prev_task["id"] < task_id):
                        prev_constraint = self.get_task_constraint(prev_task["id"])
                        break

            # Set agent busy
            self.set_agent_busy(agent)

            # Execute task
            print(f"[{agent}] Executing Task {task_id}: {task['action']} {task['object']}")
            constraint = self._execute_task(task, prev_constraint)

            # Store constraint
            if constraint:
                self.set_task_constraint(task_id, constraint)

            # Mark completed
            self.mark_task_completed(task_id)

            # Set agent free
            self.set_agent_free(agent)

            time.sleep(0.05)

        print(f"[{agent}] Worker finished")

    def _get_next_available_task(self, agent):
        """Get next available task for the agent"""
        with self.task_pool_lock:
            for i, task in enumerate(self.available_tasks):
                if task["agent"] != agent:
                    continue

                task_id = task["id"]

                # Check if already completed
                if self.is_task_completed(task_id):
                    continue

                # Check dependencies
                deps_satisfied = True
                if task_id in self.dependency_map:
                    for dep_id in self.dependency_map[task_id]:
                        if not self.is_task_completed(dep_id):
                            deps_satisfied = False
                            break

                if deps_satisfied:
                    # Remove from pool and return
                    self.available_tasks.pop(i)
                    return task

            return None

    def _all_tasks_completed(self):
        """Check if all tasks are completed"""
        with self.completion_lock:
            return len(self.completed_tasks) == len(self.task_map)

    def _wait_for_dependencies(self, task_id):
        """Wait for all dependencies to complete"""
        if task_id in self.dependency_map:
            deps = self.dependency_map[task_id]
            for dep_id in deps:
                while not self.is_task_completed(dep_id):
                    time.sleep(0.05)

    def _execute_task(self, task, constraint):
        """Execute a single task"""
        agent = task["agent"]
        action = task["action"]
        obj = task["object"]
        dest = task["destination"]

        if agent not in self.robot_ids:
            return constraint

        robot_id = self.robot_ids[agent]

        try:
            if action == "pick" and obj in self.object_map:
                pos = robot_action.get_position(self.object_map[obj])
                constraint = robot_action.pick(robot_id, self.object_map[obj], pos)
                if constraint is None:
                    print(f"  Pick action failed for object: {obj}")
                return constraint

            elif action == "place":
                if dest in self.object_map:
                    pos = robot_action.get_position(self.object_map[dest])
                else:
                    pos = robot_action.get_position(self.object_map.get(obj, obj))
                robot_action.place(agent, pos, constraint, self.robot_ids)
                return None

            elif action == "move":
                handoff_label = f"{agent}to{dest}"
                target_pos = self.get_transfer_position(handoff_label)
                if constraint:
                    robot_action.place(agent, target_pos, constraint, self.robot_ids)
                    return None

            elif action == "sweep":
                if obj in self.object_map:
                    obj_id = self.object_map[obj]
                    robot_action.sweep(robot_id, obj_id, sweep_count=3)
                else:
                    print(f"  Object {obj} not found for sweeping.")

        except Exception as e:
            print(f"Error executing {action} for {agent}: {e}")

        return constraint


def run_from_json(json_file, robot_ids, object_map, transfer_positions=None):
    executor = RobotExecutor(robot_ids, object_map, transfer_positions)
    executor.print_transfer_positions()
    executor.run_from_json(json_file)