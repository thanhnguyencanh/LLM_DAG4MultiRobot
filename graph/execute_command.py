import threading
from collections import defaultdict
import json
from robot import robot_action


#Sửa lai jauto tính transfer position
ROBOT_TRANSFER_POSITIONS = {
    "robot1": [0.65, -0.2, 0.85],
    "robot2": [0.5, 0.2, 0.85],
    "robot3": [0.35, 0.1, 0.85],
}


class RobotExecutor:
    def __init__(self, robot_ids, object_map, transfer_positions=None):
        self.robot_ids = robot_ids
        self.object_map = object_map
        self.transfer_positions = transfer_positions or ROBOT_TRANSFER_POSITIONS
        self._validate_robots()

    def _validate_robots(self):
        missing_positions = []
        for robot in self.robot_ids.keys():
            if robot not in self.transfer_positions:
                missing_positions.append(robot)

        if missing_positions:
            print(f"Warning: Missing transfer positions for: {missing_positions}")
            print(f"   Available positions: {list(self.transfer_positions.keys())}")

    def get_transfer_position(self, robot_name):
        if robot_name in self.transfer_positions:
            return self.transfer_positions[robot_name]
        else:
            print(f"No transfer position defined for {robot_name}, using default")
            return [0.5, 0.0, 0.85]

    def run_from_json(self, json_file):
        with open(json_file) as f:
            commands = json.load(f)

        waves = defaultdict(list)
        for cmd in commands:
            waves[cmd["wave"]].append(cmd)

        # Group waves into execution threads
        execution_threads = self._group_execution_threads(waves)

        # Execute each thread sequentially
        for thread_idx, thread_waves in enumerate(execution_threads):
            print(f"\n=== Execution Thread {thread_idx + 1} ===")
            print(f"Waves: {thread_waves}")
            self._execute_thread(thread_waves, waves)

    def _group_execution_threads(self, waves):
        """
        Group consecutive waves into execution threads based on boundary-agent
        non-conflict conditions.
        """
        sorted_wave_ids = sorted(waves.keys())
        execution_threads = []
        current_thread = []

        for i, wave_id in enumerate(sorted_wave_ids):
            if not current_thread:
                current_thread.append(wave_id)
            else:
                # Check if current wave can be added to current thread
                prev_wave_id = current_thread[-1]
                can_add = self._check_boundary_agent_non_conflict(
                    waves[prev_wave_id], waves[wave_id]
                )

                if can_add:
                    current_thread.append(wave_id)
                else:
                    # Start new thread
                    execution_threads.append(current_thread)
                    current_thread = [wave_id]

        if current_thread:
            execution_threads.append(current_thread)

        return execution_threads

    def _check_boundary_agent_non_conflict(self, prev_tasks, curr_tasks):
        """
        Check boundary-agent non-conflict conditions between two consecutive waves.

        Conditions:
        - Agent(start(W_i)) != Agent(start(W_{i+1}))
        - Agent(end(W_i)) != Agent(end(W_{i+1}))
        """
        if not prev_tasks or not curr_tasks:
            return True

        # Get first agent of previous wave
        prev_start_agent = prev_tasks[0]["agent"]
        # Get last agent of previous wave
        prev_end_agent = prev_tasks[-1]["agent"]

        # Get first agent of current wave
        curr_start_agent = curr_tasks[0]["agent"]
        # Get last agent of current wave
        curr_end_agent = curr_tasks[-1]["agent"]

        # Check non-conflict conditions
        start_conflict = prev_start_agent == curr_start_agent
        end_conflict = prev_end_agent == curr_end_agent

        if start_conflict or end_conflict:
            return False

        return True

    def _execute_thread(self, thread_waves, waves):
        """
        Execute all waves in a thread in parallel.
        Each wave is executed as a separate thread.
        """
        threads = []

        for wave_id in thread_waves:
            tasks = waves[wave_id]
            thread = threading.Thread(
                target=self._execute_wave_sequential,
                args=(wave_id, tasks)
            )
            threads.append(thread)
            thread.start()

        # Wait for all waves to complete
        for thread in threads:
            thread.join()

        print(f"All waves {thread_waves} completed")

    def _execute_wave_sequential(self, wave_id, tasks):
        """
        Execute all tasks within a wave sequentially.
        """
        print(f"Wave {wave_id}: Starting execution")
        constraint = None

        for task in tasks:
            constraint = self._execute_task(task, constraint)

        print(f"Wave {wave_id}: Completed")

    def _execute_task(self, task, constraint):
        """
        Execute a single task with its constraint from previous task.
        """
        agent = task["agent"]
        action = task["action"]
        obj = task["object"]
        dest = task["destination"]

        if agent not in self.robot_ids:
            return constraint

        robot_id = self.robot_ids[agent]

        try:
            print(f"  Executing: {agent} {action} {obj} -> {dest}")

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
                target_pos = self.get_transfer_position(dest)
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
    executor.run_from_json(json_file)