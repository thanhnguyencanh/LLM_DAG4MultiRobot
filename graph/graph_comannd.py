import threading
from robot import robot_action
from collections import defaultdict
import json

task_plan = [
    ("robot", "pick cake"),
    ("robot", "place cake in Box2"),
    ("human", "pick teddy bear"),
    ("human", "place teddy bear in Box1"),
    ("robot", "pick toy car"),
    ("robottohuman", "move toy car to human"),
    ("human", "pick toy car"),
    ("human", "place toy car in Box1"),
    ("human", "pick apple"),
    ("humantorobot", "move apple to robot"),
    ("robot", "pick apple"),
    ("robot", "place apple in Box2"),
]

class TaskProcessor:
    def __init__(self, task_plan):
        self.task_plan = task_plan
        self.tasks = {}
        self.edges = []
        self.lane_human = []
        self.lane_robot = []
        self.lane_transfer = []
        self._process_tasks()

    def _process_tasks(self):
        handoff_tracker = {"robottohuman": None, "humantorobot": None}
        last_task_for_object = {}
        for i, (agent, action) in enumerate(self.task_plan, start=1):
            parsed = self._parse_action(action)
            self.tasks[i] = {"agent": agent, "action": action, **parsed}

            obj = parsed["object"]

            # Lane tracking
            if agent == "human":
                self.lane_human.append(i)
            elif agent == "robot":
                self.lane_robot.append(i)
            elif agent == "humantorobot" or agent == "robottohuman":
                self.lane_transfer.append(i)
            # Handoff nodes
            if agent in ["robottohuman", "humantorobot"]:
                if obj and obj in last_task_for_object:
                    self.edges.append((last_task_for_object[obj], i))
                handoff_tracker[agent] = i

            elif not (
                    (agent == "human" and handoff_tracker["robottohuman"]) or
                    (agent == "robot" and handoff_tracker["humantorobot"])
            ):
                if obj and obj in last_task_for_object:
                    self.edges.append((last_task_for_object[obj], i))

            if agent == "human" and handoff_tracker["robottohuman"]:
                self.edges.append((handoff_tracker["robottohuman"], i))
                handoff_tracker["robottohuman"] = None

            if agent == "robot" and handoff_tracker["humantorobot"]:
                self.edges.append((handoff_tracker["humantorobot"], i))
                handoff_tracker["humantorobot"] = None

            if obj:
                last_task_for_object[obj] = i

        orphaned = [k for k, v in handoff_tracker.items() if v is not None]
        if orphaned:
            raise ValueError(f"Orphaned handoffs: {orphaned}")
        #xu ly wave

    def waveprocess(self):
        # Tạo adjacency list và in-degree
        adj = defaultdict(list)
        indeg = defaultdict(int)
        for u, v in self.edges:
            adj[u].append(v)
            indeg[v] += 1

        # Tìm tất cả node đầu chuỗi (indegree = 0)
        start_nodes = [node for node in self.tasks.keys() if indeg[node] == 0]
        if not start_nodes:
            # Nếu không có node indegree=0, tìm node có indegree nhỏ nhất
            min_indeg = min(indeg[node] for node in self.tasks.keys())
            start_nodes = [node for node in self.tasks.keys() if indeg[node] == min_indeg]

        visited_global = set()
        chains = []

        def traverse_chain_from_start(start_node):
            """Duyệt toàn bộ chuỗi từ node đầu tiên"""
            chain = []
            stack = [start_node]
            visited_local = set()

            while stack:
                node = stack.pop()
                if node in visited_local or node in visited_global:
                    continue

                chain.append(node)
                visited_local.add(node)
                visited_global.add(node)

                # Thêm tất cả node con vào stack
                if node in adj:
                    for next_node in adj[node]:
                        if next_node not in visited_local:
                            stack.append(next_node)

            return sorted(chain)  # Sort để có thứ tự consistent

        # Duyệt từ mỗi node đầu chuỗi
        for start_node in sorted(start_nodes):
            if start_node not in visited_global:
                chain = traverse_chain_from_start(start_node)
                if chain:
                    chains.append(chain)

        # Xử lý các node còn lại (nếu có)
        remaining_nodes = set(self.tasks.keys()) - visited_global
        for node in sorted(remaining_nodes):
            chains.append([node])

        # Phân loại chuỗi: có transfer hay không
        chains_with_transfer = []
        chains_without_transfer = []

        for chain in chains:
            has_transfer = any(node in self.lane_transfer for node in chain)
            if has_transfer:
                chains_with_transfer.append(chain)
            else:
                chains_without_transfer.append(chain)

        # Gán wave
        wave_assignment = {}
        current_wave = 1

        # Tất cả chuỗi không có transfer cùng wave 1
        if chains_without_transfer:
            for chain in chains_without_transfer:
                for node in chain:
                    wave_assignment[node] = current_wave
            current_wave += 1

        # Mỗi chuỗi có transfer là một wave riêng
        for chain in chains_with_transfer:
            for node in chain:
                wave_assignment[node] = current_wave
            current_wave += 1

        # Thêm thông tin wave vào tasks
        for task_id, wave in wave_assignment.items():
            self.tasks[task_id]["wave"] = wave

        # In kết quả debug
        print("\n=== Wave Assignment ===")
        print("Chains found:")
        for i, chain in enumerate(chains, 1):
            has_transfer = any(node in self.lane_transfer for node in chain)
            print(f"  Chain {i}: {chain} {'(có transfer)' if has_transfer else '(không transfer)'}")

        print("\nWave assignments:")
        for wave in range(1, current_wave):
            wave_tasks = [tid for tid, task in self.tasks.items() if task.get("wave") == wave]
            print(f"Wave {wave}: {wave_tasks}")
            for tid in wave_tasks:
                task = self.tasks[tid]
                print(f"  Task {tid}: {task['agent']} - {task['action']}")

        return wave_assignment


    def debug_print_graph(self):
        adj = defaultdict(list)
        indeg = defaultdict(int)
        for u, v in self.edges:
            adj[u].append(v)
            indeg[v] += 1

        visited_chain = set()

        def build_chain(start):
            chain = [start]
            cur = start
            while cur in adj and len(adj[cur]) == 1 and indeg[adj[cur][0]] == 1:
                nxt = adj[cur][0]
                if nxt in visited_chain:
                    break
                chain.append(nxt)
                visited_chain.add(nxt)
                cur = nxt
            return chain

        for node in sorted(self.tasks.keys()):
            if node in visited_chain:
                continue
            # Nếu node này là đầu chuỗi (indeg = 0 hoặc >1)
            if indeg[node] != 1:
                chain = build_chain(node)
                if len(chain) > 1:
                    print(" -> ".join(map(str, chain)))
                else:
                    # Node đứng 1 mình
                    if node in adj:
                        for v in adj[node]:
                            print(f"{node} -> {v}")
            visited_chain.update(chain)

        print("\n=== Lane của agent ===")
        print(f"Lane robot: {self.lane_robot}")
        print(f"Lane human: {self.lane_human}")
        print(f"Lane transfer: {self.lane_transfer}")


    def _parse_action(self, action_text):
        if not action_text:
            return {"verb": "unknown", "object": "", "destination": None}

        action_text = action_text.strip().lower()

        if action_text.startswith("move "):
            parts = action_text[5:].split(" to ")
            if len(parts) == 2:
                return {"verb": "move", "object": parts[0].strip(), "destination": parts[1].strip()}
            return {"verb": "move", "object": parts[0].strip(), "destination": None}

        elif action_text.startswith("place "):
            parts = action_text[6:].split(" in ")
            if len(parts) == 2:
                return {"verb": "place", "object": parts[0].strip(), "destination": parts[1].strip()}
            return {"verb": "place", "object": parts[0].strip(), "destination": None}

        elif action_text.startswith("pick "):
            return {"verb": "pick", "object": action_text[5:].strip(), "destination": None}

        return {"verb": "unknown", "object": action_text, "destination": None}

    def _get_ready_tasks(self, visited_set, prev_map):
        return [tid for tid in sorted(self.tasks.keys())
                if tid not in visited_set and
                all(dep in visited_set for dep in prev_map[tid])]

    def export_json(self, filename="commands.json"):
        prev_map = defaultdict(set)
        for u, v in self.edges:
            prev_map[v].add(u)

        visited = set()
        json_list = []
        cmd_id = 1

        while len(visited) < len(self.tasks):
            ready_tasks = self._get_ready_tasks(visited, prev_map)
            if not ready_tasks:
                break

            tid = ready_tasks[0]
            task = self.tasks[tid]
            agent = task["agent"]

            if agent in ["robottohuman", "humantorobot"]:
                if agent == "robottohuman":
                    move_agent = "robot"
                    lane = "transfer"
                else:  # humantorobot
                    move_agent = "human"
                    lane = "transfer"
            else:
                move_agent = agent
                lane = agent

            json_list.append({
                "id": cmd_id,
                "agent": move_agent,
                "action": task["verb"],
                "object": (task["object"] or "").replace(" ", "_"),
                "destination": (task["destination"] or "").replace(" ", "_"),
                "lane": lane,
                "wave": task.get("wave", None)
            })

            cmd_id += 1
            visited.add(tid)

        with open(filename, "w") as f:
            json.dump(json_list, f, indent=4)
        print(f"JSON command file saved to {filename}")


def run_from_json(json_file, robot_ids, object_map, basket):
    with open(json_file) as f:
        cmds = json.load(f)

    waves = {}
    for task in cmds:
        wave_id = task["wave"]
        if wave_id not in waves:
            waves[wave_id] = []
        waves[wave_id].append(task)

    current_constraint = None

    # Xử lý từng wave
    for wave_id, wave_tasks in sorted(waves.items()):
        lanes = set(task["lane"] for task in wave_tasks)
        print(f"Wave {wave_id}:")

        if "transfer" in lanes:
            state = 0  # làm cùng nhau
            print("  → Làm cùng nhau")
        else:
            state = 1  # làm song song
            print("  → Làm song song")

        # Xử lý từng task trong wave
        for c in wave_tasks:
            agent = c.get('agent', '').lower()
            action = c.get('action', '').lower()
            obj = c.get('object', '').lower().strip()
            dst = c.get('destination', '').lower().strip()

            if agent not in robot_ids:
                print(f"[WARN] Agent '{agent}' không tồn tại trong robot_ids")
                continue

            this_robot_id = robot_ids[agent]
            robot_pos = [0.8, 0.2, 0.65]
            human_pos = [0.3, -0.2, 0.65]

            # Xác định target
            target_key = None
            if obj:
                if obj in object_map:
                    target_key = obj
                else:
                    print(f"[WARN] Không tìm thấy object hợp lệ: obj='{obj}'")
                    continue
            elif dst:
                if dst in object_map or dst in basket:
                    target_key = dst
                elif dst in robot_ids:
                    target_key = None
                else:
                    print(f"[WARN] Không tìm thấy destination hợp lệ: dst='{dst}'")
                    continue

            # Thực hiện hành động
            if state == 0:
                # Làm cùng nhau
                if action == 'pick':
                    if target_key is None:
                        print(f"[WARN] Pick action nhưng không có target_key hợp lệ.")
                        continue
                    pos = robot_action.get_position(object_map[target_key])
                    current_constraint = robot_action.pick(this_robot_id, object_map[target_key], pos)

                elif action == 'move' and dst == 'robot':
                    robot_action.move_to_target(this_robot_id, robot_pos, current_constraint)
                    if current_constraint is not None:
                        robot_action.place(agent, human_pos, current_constraint, robot_ids)
                        current_constraint = None

                elif action == 'move' and dst == 'human':
                    robot_action.move_to_target(this_robot_id, human_pos, current_constraint)
                    if current_constraint is not None:
                        robot_action.place(agent, robot_pos, current_constraint, robot_ids)
                        current_constraint = None

                elif action == 'place':
                    if target_key is None:
                        print(f"[WARN] Place action nhưng không có target_key hợp lệ.")
                        continue
                    if dst in basket:
                        pos = basket[dst]["center"]
                    else:
                        pos = robot_action.get_position(object_map[target_key])
                    robot_action.place(agent, pos, current_constraint, robot_ids)
                    current_constraint = None
            else:
                # Làm song song
                work_threading(wave_tasks,robot_ids, object_map, basket)
                break

def work_threading(wave_tasks, robot_ids, object_map, basket):
# Nhóm các task theo agent
    tasks_per_agent = {}
    for task in wave_tasks:
        agent = task.get("agent", "").lower()
        if agent not in tasks_per_agent:
            tasks_per_agent[agent] = []
        tasks_per_agent[agent].append(task)

    # Hàm chạy các task của từng agent
    def run_tasks(agent, tasks):
        if agent not in robot_ids:
            print(f"[ERROR] Agent '{agent}' không tồn tại trong robot_ids: {list(robot_ids.keys())}")
            return
        this_agent_id = robot_ids[agent]
        current_constraint = None

        for task in tasks:
            agent = task.get("agent", "").lower()
            action = task.get("action", "").lower()
            obj = task.get("object", "")
            dst = task.get("destination", "")

            obj_key = obj.replace(" ", "_") if obj else None
            dst_key = dst.replace(" ", "_") if dst else None

            print(f"[INFO] Agent {agent} (ID: {this_agent_id}) executing: {action} {obj_key or ''} {dst_key or ''}")

            try:
                if action == "pick":
                    if obj_key not in object_map:
                        print(f"[WARN] Object '{obj_key}' không tồn tại trong object_map")
                        continue
                    pos = robot_action.get_position(object_map[obj_key])
                    current_constraint = robot_action.pick(this_agent_id, object_map[obj_key], pos)

                elif action == "place":
                    if current_constraint is None:
                        print(f"[WARN] Không có object để place cho agent {agent}")
                        continue

                    if dst_key in basket:
                        pos = basket[dst_key]["center"]
                    elif obj_key in object_map:
                        pos = robot_action.get_position(object_map[obj_key])
                    else:
                        print(f"[WARN] Không tìm thấy vị trí cho place: obj='{obj_key}', dst='{dst_key}'")
                        continue

                    robot_action.place(agent, pos, current_constraint, robot_ids)
                    current_constraint = None

                elif action == "move":
                    if dst_key == "robot":
                        target_pos = [0.8, 0.2, 0.65]
                    elif dst_key == "human":
                        target_pos = [0.3, -0.2, 0.65]
                    else:
                        print(f"[WARN] Destination '{dst_key}' không được hỗ trợ cho move action")
                        continue

                    robot_action.move_to_target(this_agent_id, target_pos, current_constraint)

                    # Nếu đang kẹp vật, thả xuống vị trí hiện tại
                    if current_constraint is not None:
                        robot_action.place(agent, target_pos, current_constraint, robot_ids)
                        current_constraint = None

                else:
                    print(f"[WARN] Action '{action}' không được hỗ trợ")

            except Exception as e:
                print(f"[ERROR] Lỗi khi thực hiện action {action} cho agent {agent}: {e}")

    # Tạo thread cho mỗi agent và chạy song song
    threads = []
    for agent, tasks in tasks_per_agent.items():
        thread = threading.Thread(target=run_tasks, args=(agent, tasks))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()





