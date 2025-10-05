import threading
from collections import defaultdict
import json
from robot import robot_action

#check lại cái này để thêm vị trí handoff cho task2 cungx như cái khác automation

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
            print(f" Warning: Missing transfer positions for: {missing_positions}")
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

        wave_groups = self._group_sequential_waves(waves)

        for wave_group in wave_groups:
            if len(wave_group) == 1:
                wave_id = wave_group[0]
                tasks = waves[wave_id]
                has_transfer = any(t["lane"] == "transfer" for t in tasks)

                if has_transfer:
                    print(f" Wave {wave_id}: Sequential execution")
                    self._execute_sequential(tasks)
                else:
                    print(f" Wave {wave_id}: Parallel execution")
                    self._execute_parallel(tasks)
            else:
                # Multiple sequential waves with different starting agents - run in parallel
                print(f"Waves {wave_group}: Parallel execution of sequential waves")
                self._execute_sequential_waves_parallel(wave_group, waves)

    def _group_sequential_waves(self, waves):
        wave_groups = []
        current_group = []
        sorted_waves = sorted(waves.keys())
        for i, wave_id in enumerate(sorted_waves):
            tasks = waves[wave_id]
            has_transfer = any(t["lane"] == "transfer" for t in tasks)
            if has_transfer:
                if not current_group:
                    current_group = [wave_id]
                else:
                    can_group = True
                    current_first_agent = tasks[0]["agent"] if tasks else None

                    for prev_wave_id in current_group:
                        prev_tasks = waves[prev_wave_id]
                        prev_first_agent = prev_tasks[0]["agent"] if prev_tasks else None

                        if current_first_agent == prev_first_agent:
                            can_group = False
                            break

                    if can_group:
                        current_group.append(wave_id)
                    else:
                        wave_groups.append(current_group)
                        current_group = [wave_id]
            else:
                if current_group:
                    wave_groups.append(current_group)
                    current_group = []
                wave_groups.append([wave_id])

        if current_group:
            wave_groups.append(current_group)

        return wave_groups

    def _execute_sequential_waves_parallel(self, wave_group, waves):
        threads = []

        for wave_id in wave_group:
            tasks = waves[wave_id]
            thread = threading.Thread(target=self._execute_sequential, args=(tasks,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _execute_sequential(self, tasks):
        constraint = None
        for task in tasks:
            constraint = self._execute_task(task, constraint)

    def _execute_parallel(self, tasks):
        agent_tasks = defaultdict(list)
        for task in tasks:
            agent_tasks[task["agent"]].append(task)

        threads = []
        for agent, task_list in agent_tasks.items():
            thread = threading.Thread(target=self._execute_agent_tasks,
                                      args=(agent, task_list))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _execute_agent_tasks(self, agent, tasks):
        constraint = None
        for task in tasks:
            constraint = self._execute_task(task, constraint)

    def _execute_task(self, task, constraint):
        agent = task["agent"]
        action = task["action"]
        obj = task["object"]
        dest = task["destination"]

        if agent not in self.robot_ids:
            return constraint

        robot_id = self.robot_ids[agent]

        try:
            print(f"Executing: {agent} {action} {obj} {dest}")

            if action == "pick" and obj in self.object_map:
                pos = robot_action.get_position(self.object_map[obj])
                constraint = robot_action.pick(robot_id, self.object_map[obj], pos)
                if constraint is None:
                    print(f"Pick action failed for object: {obj}")
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
                    print(f"Object {obj} not found for sweeping.")

        except Exception as e:
            print(f"Error executing {action} for {agent}: {e}")

        return constraint

def run_from_json(json_file, robot_ids, object_map, transfer_positions=None):
    executor = RobotExecutor(robot_ids, object_map, transfer_positions)
    executor.run_from_json(json_file)