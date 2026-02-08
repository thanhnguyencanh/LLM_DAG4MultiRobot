"""
Robot Executor Module
Handles multi-robot task execution with parallel processing and dependency management.
"""

import threading
from collections import defaultdict
import json
import time
from robot import robot_action
from Task1.environment import Environment  # Define your environment class here ( Modify)


class RobotExecutor:
    """
    Executes robot tasks from JSON with multi-threaded parallel execution.
    
    Features:
    - Multi-agent parallel execution using threads
    - Task dependency management
    - Handoff point coordination between robots
    - Thread-safe state tracking
    """
    
    def __init__(self, robot_ids, object_map, transfer_positions=None):
        """
        Initialize executor with robots and environment.
        
        Args:
            robot_ids: Dict mapping agent names to robot instances
            object_map: Dict mapping object names to PyBullet IDs
            transfer_positions: Dict of handoff points (optional)
        """
        self.robot_ids = robot_ids
        self.object_map = object_map

        # Agent state: tracks if agent is holding an object (thread-safe)
        self.agent_holding = {agent: False for agent in robot_ids.keys()}
        self.holding_lock = threading.Lock()

        # Task completion tracking (thread-safe)
        self.completed_tasks = set()
        self.completion_lock = threading.Lock()

        # Constraint tracking for pick/place operations (thread-safe)
        self.task_constraints = {}
        self.constraint_lock = threading.Lock()

        # Global task pool for work distribution (thread-safe)
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

    def set_agent_holding(self, agent, holding=True):
        """Set agent's holding state"""
        with self.holding_lock:
            self.agent_holding[agent] = holding
            status = "HOLDING object" if holding else "FREE (hands empty)"
            print(f"  [{agent}]: {status}")

    def is_agent_holding(self, agent):
        """Check if agent is holding an object"""
        with self.holding_lock:
            return self.agent_holding[agent]

    def mark_task_completed(self, task_id):
        with self.completion_lock:
            self.completed_tasks.add(task_id)
            print(f"  [Task {task_id}] Completed")

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
        print("EXECUTION PLAN - OPTIMIZED PARALLEL EXECUTION")
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

        print("\nAll tasks completed!")

    def _build_dependency_map(self, commands):
        """Build dependency map from explicit node dependencies in JSON"""
        dependency_map = defaultdict(list)

        for cmd in commands:
            task_id = cmd["id"]
            node_str = cmd.get("node", "node[]")

            if "node[" in node_str:
                start = node_str.index("[") + 1
                end = node_str.index("]")
                deps_str = node_str[start:end].strip()

                if deps_str:
                    dep_ids = [int(d.strip()) for d in deps_str.split(",")]
                    dependency_map[task_id] = dep_ids

        print("\n[Dependency Map]")
        if dependency_map:
            for task_id in sorted(dependency_map.keys()):
                deps = dependency_map[task_id]
                print(f"  Task {task_id} depends on: {deps}")
        else:
            print("No dependencies found")
        print()

        return dependency_map

    def _agent_worker(self, agent):
        """
        Worker thread for each agent.

        KEY LOGIC:
        1. Agent picks task that belongs to it
        2. Check dependencies satisfied
        3. For PICK: agent must not be holding anything
        4. Execute immediately when conditions met
        """
        print(f"\n[{agent}] Worker started")

        while True:
            # Try to get next available task for this agent
            task = self._get_next_available_task(agent)

            if task is None:
                # No more tasks available
                if self._all_tasks_completed():
                    print(f"[{agent}] All tasks done, shutting down")
                    break
                else:
                    # Wait a bit for dependencies or other agents
                    time.sleep(0.05)
                    continue

            task_id = task["id"]
            action = task["action"]
            obj = task["object"]

            # Wait for dependencies BEFORE executing
            self._wait_for_dependencies(task_id)

            # Get constraint from previous pick if needed
            prev_constraint = None
            if action in ["place", "move"]:
                for prev_task in self.task_map.values():
                    if (prev_task["agent"] == agent and
                            prev_task["object"] == obj and
                            prev_task["action"] == "pick" and
                            prev_task["id"] < task_id):
                        prev_constraint = self.get_task_constraint(prev_task["id"])
                        break

            # Execute task
            print(f"[{agent}] Executing Task {task_id}: {action} {obj}")
            constraint = self._execute_task(task, prev_constraint)

            # Update agent holding state based on action
            if action == "pick" and constraint:
                self.set_agent_holding(agent, True)
                self.set_task_constraint(task_id, constraint)
            elif action in ["place", "move"]:
                self.set_agent_holding(agent, False)

            # Mark task as completed
            self.mark_task_completed(task_id)

            # NO SLEEP HERE - immediately try to get next task!
            # This allows agent to pick next task ASAP after completing current one

        print(f"[{agent}] Worker finished")

    def _get_next_available_task(self, agent):
        """
        Get next available task for the agent.

        CONDITIONS:
        1. Task must belong to this agent
        2. Task not already completed
        3. All dependencies satisfied
        4. For PICK action: agent must not be holding anything
        """
        with self.task_pool_lock:
            for i, task in enumerate(self.available_tasks):
                # Condition 1: Must be this agent's task
                if task["agent"] != agent:
                    continue

                task_id = task["id"]

                # Condition 2: Not already completed
                if self.is_task_completed(task_id):
                    continue

                # Condition 4: For PICK, agent must not be holding anything
                if task["action"] == "pick":
                    if self.is_agent_holding(agent):
                        # Agent still holding object, cannot pick new one
                        continue

                # Condition 3: Check dependencies
                deps_satisfied = True
                if task_id in self.dependency_map:
                    for dep_id in self.dependency_map[task_id]:
                        if not self.is_task_completed(dep_id):
                            deps_satisfied = False
                            break

                if deps_satisfied:
                    # Found valid task - remove from pool and return
                    self.available_tasks.pop(i)
                    print(f"  [{agent}] Selected Task {task_id} from pool")
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
            waiting_for = [d for d in deps if not self.is_task_completed(d)]

            if waiting_for:
                print(f"    Task {task_id} waiting for: {waiting_for}")

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
                    print(f"    Pick action failed for object: {obj}")
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