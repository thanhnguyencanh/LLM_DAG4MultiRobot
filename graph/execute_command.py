import threading
from collections import defaultdict
import json
from robot import robot_action
from Task2.environment import Environment


class RobotExecutor:
    def __init__(self, robot_ids, object_map, transfer_positions=None):
        """
        Args:
            robot_ids: Dict mapping robot names to robot IDs
            object_map: Dict mapping object names to object IDs
            transfer_positions: Dict with transfer positions
                               (nếu None sẽ lấy từ Environment)
        """
        self.robot_ids = robot_ids
        self.object_map = object_map

        # Lấy transfer positions từ Environment nếu không được cung cấp
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
                "Please define handoff_points (e.g., {'robot1torobot2': [x, y, z], ...}) in Environment"
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
        """In ra tất cả handoff points"""
        print("\n" + "=" * 60)
        print(" HANDOFF POINTS (for move action)")
        print("=" * 60)
        for key, pos in sorted(self.transfer_positions.items()):
            print(f"{key}: {pos}")
        print("=" * 60 + "\n")

    def run_from_json(self, json_file):
        """Chạy commands từ JSON file"""
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
        """Nhóm waves thành execution threads"""
        sorted_wave_ids = sorted(waves.keys())
        execution_threads = []
        remaining_waves = sorted_wave_ids.copy()  # Các wave chưa được xử lý

        while remaining_waves:
            current_thread = []
            waves_to_remove = []

            # Bắt đầu thread mới với wave đầu tiên còn lại
            current_thread.append(remaining_waves[0])
            waves_to_remove.append(remaining_waves[0])

            # Thử thêm các wave tiếp theo vào thread
            for wave_id in remaining_waves[1:]:
                # Kiểm tra với TẤT CẢ wave đã có trong thread hiện tại
                can_add = True
                for existing_wave_id in current_thread:
                    if not self._check_boundary_agent_non_conflict(
                            waves[existing_wave_id],
                            waves[wave_id]
                    ):
                        can_add = False
                        break  # Nếu conflict với bất kỳ wave nào → dừng kiểm tra

                if can_add:
                    current_thread.append(wave_id)
                    waves_to_remove.append(wave_id)
                else:
                    # Gặp conflict → dừng việc thêm vào thread này
                    break

            # Lưu thread và loại bỏ các wave đã xử lý
            execution_threads.append(current_thread)
            for wave_id in waves_to_remove:
                remaining_waves.remove(wave_id)

        return execution_threads

    def _check_boundary_agent_non_conflict(self, prev_tasks, curr_tasks):
        """Kiểm tra xem hai wave có conflict không"""
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
                # Chuyển destination robot name thành handoff label (e.g., robot1 -> robot2torobot1)
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