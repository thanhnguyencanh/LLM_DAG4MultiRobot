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

    for wave_id in sorted(waves.keys()):
        tasks = waves[wave_id]
        has_transfer = any(t["lane"] == "transfer" for t in tasks)

        if has_transfer:
            print(f"Wave {wave_id}: Sequential execution")
            _execute_sequential(tasks, robot_ids, object_map)
        else:
            print(f"Wave {wave_id}: Parallel execution")
            _execute_parallel(tasks, robot_ids, object_map)

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
            return robot_action.pick(robot_id, object_map[obj], pos)

        elif action == "place":
            if dest in object_map:
                pos = robot_action.get_position(object_map[dest])
            else:
                pos = robot_action.get_position(object_map.get(obj, obj))
            robot_action.place(agent, pos, constraint, robot_ids)
            return None

        elif action == "move":
            target_pos = [0.33, -0.2, 0.65] if dest == "robot" else [0.7, 0.2, 0.65]
            robot_action.move_to_target(robot_id, target_pos, constraint)
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