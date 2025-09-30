import threading
from collections import defaultdict
import json
from robot import robot_action

def run_from_json(json_file, robot_ids, object_map):
    with open(json_file) as f:
        commands = json.load(f)

    waves = defaultdict(list)
    for cmd in commands:
        waves[cmd["wave"]].append(cmd)

    # Group consecutive sequential waves that can run in parallel
    wave_groups = _group_sequential_waves(waves)

    for wave_group in wave_groups:
        if len(wave_group) == 1:
            # Single wave - execute normally
            wave_id = wave_group[0]
            tasks = waves[wave_id]
            has_transfer = any(t["lane"] == "transfer" for t in tasks)

            if has_transfer:
                print(f"Wave {wave_id}: Sequential execution")
                _execute_sequential(tasks, robot_ids, object_map)
            else:
                print(f"Wave {wave_id}: Parallel execution")
                _execute_parallel(tasks, robot_ids, object_map)
        else:
            # Multiple sequential waves with different starting agents - run in parallel
            print(f"Waves {wave_group}: Parallel execution of sequential waves")
            _execute_sequential_waves_parallel(wave_group, waves, robot_ids, object_map)


def _group_sequential_waves(waves):
    """Group consecutive sequential waves that can run in parallel"""
    wave_groups = []
    current_group = []

    sorted_waves = sorted(waves.keys())

    for i, wave_id in enumerate(sorted_waves):
        tasks = waves[wave_id]
        has_transfer = any(t["lane"] == "transfer" for t in tasks)

        if has_transfer:  # Sequential wave
            if not current_group:
                # Start new group with this sequential wave
                current_group = [wave_id]
            else:
                # Check if this sequential wave can be grouped with previous ones
                can_group = True

                # Get first agent of current wave
                current_first_agent = tasks[0]["agent"] if tasks else None

                # Check against first agents of waves in current group
                for prev_wave_id in current_group:
                    prev_tasks = waves[prev_wave_id]
                    prev_first_agent = prev_tasks[0]["agent"] if prev_tasks else None

                    if current_first_agent == prev_first_agent:
                        can_group = False
                        break

                if can_group:
                    current_group.append(wave_id)
                else:
                    # Cannot group - finalize current group and start new one
                    wave_groups.append(current_group)
                    current_group = [wave_id]
        else:
            # Parallel wave - finalize current group if exists, then add this wave alone
            if current_group:
                wave_groups.append(current_group)
                current_group = []
            wave_groups.append([wave_id])

    # Add remaining group if exists
    if current_group:
        wave_groups.append(current_group)

    return wave_groups


def _execute_sequential_waves_parallel(wave_group, waves, robot_ids, object_map):
    """Execute multiple sequential waves in parallel"""
    threads = []

    for wave_id in wave_group:
        tasks = waves[wave_id]
        thread = threading.Thread(target=_execute_sequential,
                                  args=(tasks, robot_ids, object_map))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


# Execute tasks in sequential order
def _execute_sequential(tasks, robot_ids, object_map):
    constraint = None
    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, constraint)


# execute tasks in parallel
def _execute_parallel(tasks, robot_ids, object_map):
    agent_tasks = defaultdict(list)
    for task in tasks:
        agent_tasks[task["agent"]].append(task)

    threads = []
    for agent, task_list in agent_tasks.items():
        thread = threading.Thread(target=_execute_agent_tasks,
                                  args=(agent, task_list, robot_ids, object_map))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


# Execute tasks for each agent in parallel
def _execute_agent_tasks(agent, tasks, robot_ids, object_map):
    constraint = None
    for task in tasks:
        constraint = _execute_task(task, robot_ids, object_map, constraint)


# Execute a single task for the agent
def _execute_task(task, robot_ids, object_map, constraint):
    agent = task["agent"]
    action = task["action"]
    obj = task["object"]
    dest = task["destination"]

    if agent not in robot_ids:
        print(f"Unknown agent: {agent}")
        return constraint

    robot_id = robot_ids[agent]

    try:
        print(f"Executing: {agent} {action} {obj} {dest}")
        if action == "pick" and obj in object_map:
            pos = robot_action.get_position(object_map[obj])
            constraint = robot_action.pick(robot_id, object_map[obj], pos)
            if constraint is None:
                print(f"Pick action failed for object: {obj}")
            return constraint

        elif action == "place":
            if dest in object_map:
                pos = robot_action.get_position(object_map[dest])
            else:
                pos = robot_action.get_position(object_map.get(obj, obj))
            robot_action.place(agent, pos, constraint, robot_ids)
            return None

        elif action == "move":
            target_pos = [0.5, 0.2, 0.85] if dest == "robot2" else [0.65, -0.2, 0.85]
            if constraint:
                robot_action.place(agent, target_pos, constraint, robot_ids)
                return None

        elif action == "sweep":
            if obj in object_map:
                obj_id = object_map[obj]
                robot_action.sweep(robot_id, obj_id, sweep_count=3)
            else:
                print(f"Object {obj} not found for sweeping.")

    except Exception as e:
        print(f"Error executing {action} for {agent}: {e}")

    return constraint