import threading
from collections import defaultdict
import json
import time
from robot import robot_action
from Task1.environment import Environment


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

        # Global task pool - tất cả tasks available
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

        # Group by waves
        waves = defaultdict(list)
        for cmd in commands:
            waves[cmd["wave"]].append(cmd)

        # Group waves into execution threads
        execution_threads = self._group_execution_threads(waves)

        print("\n" + "=" * 70)
        print("EXECUTION PLAN - PARALLEL WAVES WITH AGENT SWITCHING")
        print("=" * 70)
        for idx, thread_waves in enumerate(execution_threads):
            print(f"Thread {idx + 1}: Waves {thread_waves}")
            for wave_id in thread_waves:
                tasks = waves[wave_id]
                agents = [t["agent"] for t in tasks]
                print(f"  Wave {wave_id}: {agents}")
        print("=" * 70 + "\n")

        # Execute with wave-based parallelism and agent switching
        self._execute_waves_parallel(execution_threads, waves)

    def _build_dependency_map(self, commands):
        """Build dependency map based on task sequence"""
        dependency_map = defaultdict(list)

        # Build dependencies based on same object or transfer relationships
        for i, cmd in enumerate(commands):
            # Dependency: pick -> move/place (same object, same agent)
            if cmd["action"] == "pick":
                for future_cmd in commands[i + 1:]:
                    if (future_cmd["agent"] == cmd["agent"] and
                            future_cmd["object"] == cmd["object"] and
                            future_cmd["action"] in ["move", "place"]):
                        dependency_map[future_cmd["id"]].append(cmd["id"])
                        break

            # Dependency: move -> pick (transfer between agents)
            if cmd["action"] == "move":
                dest_agent = cmd["destination"]
                obj = cmd["object"]
                for future_cmd in commands[i + 1:]:
                    if (future_cmd["agent"] == dest_agent and
                            future_cmd["action"] == "pick" and
                            future_cmd["object"] == obj):
                        dependency_map[future_cmd["id"]].append(cmd["id"])
                        break

        print("\n[Dependency Map]")
        for task_id, deps in dependency_map.items():
            print(f"  Task {task_id} depends on: {deps}")
        print()

        return dependency_map

    def _group_execution_threads(self, waves):
        """Group waves into execution threads based on first node agent"""
        sorted_wave_ids = sorted(waves.keys())
        execution_threads = []
        remaining_waves = sorted_wave_ids.copy()

        while remaining_waves:
            current_thread = []
            waves_to_remove = []

            # Start new thread with first remaining wave
            current_thread.append(remaining_waves[0])
            waves_to_remove.append(remaining_waves[0])
            first_wave_start_agent = waves[remaining_waves[0]][0]["agent"]

            # Try to add subsequent waves to thread
            for wave_id in remaining_waves[1:]:
                curr_wave_start_agent = waves[wave_id][0]["agent"]

                # Check conflict with ALL waves in current thread
                can_add = True
                for existing_wave_id in current_thread:
                    existing_start_agent = waves[existing_wave_id][0]["agent"]
                    if curr_wave_start_agent == existing_start_agent:
                        can_add = False
                        break

                if can_add:
                    current_thread.append(wave_id)
                    waves_to_remove.append(wave_id)
                else:
                    break

            execution_threads.append(current_thread)
            for wave_id in waves_to_remove:
                remaining_waves.remove(wave_id)

        return execution_threads

    def _execute_waves_parallel(self, execution_threads, waves):
        """
        Execute waves with true parallelism:
        - Multiple waves can run simultaneously
        - Agents can switch between waves/threads when free
        """
        # Flatten all tasks and sort by wave
        all_tasks_by_wave = []
        for thread_waves in execution_threads:
            for wave_id in thread_waves:
                for task in waves[wave_id]:
                    all_tasks_by_wave.append((wave_id, task))

        # Sort by wave ID to maintain wave ordering
        all_tasks_by_wave.sort(key=lambda x: x[0])

        # Populate available tasks
        with self.task_pool_lock:
            self.available_tasks = all_tasks_by_wave.copy()

        print(f"\n[Task Pool] {len(self.available_tasks)} tasks loaded\n")

        # Start worker thread for each agent
        threads = []
        for agent in self.robot_ids.keys():
            t = threading.Thread(target=self._agent_worker, args=(agent,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        print("\n✅ All waves completed!")

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

            wave_id, task_data = task
            task_id = task_data["id"]

            # Wait for dependencies
            self._wait_for_dependencies(task_id)

            # Get constraint if needed
            prev_constraint = None
            if task_data["action"] in ["place", "move"]:
                for prev_task in self.task_map.values():
                    if (prev_task["agent"] == agent and
                            prev_task["object"] == task_data["object"] and
                            prev_task["action"] == "pick" and
                            prev_task["id"] < task_id):
                        prev_constraint = self.get_task_constraint(prev_task["id"])
                        break

            # Set agent busy
            self.set_agent_busy(agent)

            # Execute task
            print(f"[{agent}] Executing Wave {wave_id}, Task {task_id}: {task_data['action']} {task_data['object']}")
            constraint = self._execute_task(task_data, prev_constraint)

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
        """
        Get next available task for this agent.
        Task is available if:
        1. Assigned to this agent
        2. Dependencies are satisfied
        3. Not yet completed
        """
        with self.task_pool_lock:
            for i, (wave_id, task) in enumerate(self.available_tasks):
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
                    return (wave_id, task)

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