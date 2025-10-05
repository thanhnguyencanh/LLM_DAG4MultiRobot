from Task1.environment import Environment
import math
import pybullet as p

#Fix lại code để lấy từ trong môi trường simulation

AGENT_CONFIG = {
    "robot1": {
        "capabilities": """- PICK(object): move to object and pick up
            - MOVE(location): move hand/base to location
            - PLACE(object, destination): place held object into/onto destination
            - SWEEP(surface, tool): wipe/clean a surface using held object""",
        "label": "robot2"
    },
    "robot2": {
        "capabilities": """- PICK(object): move to object and pick up
        - MOVE(location): move hand/base to location
        - PLACE(object, destination): place held object into/onto destination
        - SWEEP(surface, tool): wipe/clean a surface using held object""",
        "label": "robot1"
    },
    "robot3": {
        "capabilities": """- PICK(object): move to object and pick up
        - MOVE(location): move hand/base to location
        - PLACE(object, destination): place held object into/onto destination
        - SWEEP(surface, tool): wipe/clean a surface using held object""",
        "label": "robot3"
    },
    # Thêm robot mới ở đây...
}


class PromptBuilder:
    def __init__(self, agent_config=None, use_simulation=True):
        """
        Args:
            agent_config: Dict định nghĩa agents và capabilities
                         (nếu None sẽ dùng AGENT_CONFIG mặc định)
            use_simulation: Nếu True, sẽ khởi tạo simulation để lấy position thực tế
                           Nếu False, sẽ dùng position mặc định từ config
        """
        self.agent_config = agent_config or AGENT_CONFIG
        self.env = Environment()
        self.agent_names = list(self.agent_config.keys())
        self.physics_client = None
        self.use_simulation = use_simulation

        if use_simulation:
            # Khởi tạo PyBullet physics server
            self._init_physics_server()
            # Khởi tạo simulation để lấy position
            self.env.setup_simulation()
            # Lấy position của các robot từ simulation
            self._update_robot_positions()
        else:
            # Sử dụng position mặc định nếu không dùng simulation
            self._set_default_positions()

    def _init_physics_server(self):
        """Khởi tạo PyBullet physics server"""
        try:
            # Thử kết nối với server hiện có
            p.getConnectionInfo()
            print("[INFO] Using existing PyBullet connection")
        except:
            # Nếu chưa có connection, tạo mới (DIRECT mode - không GUI)
            self.physics_client = p.connect(p.DIRECT)
            print(f"[INFO] Created new PyBullet connection: {self.physics_client}")

    def _set_default_positions(self):
        """
        Đặt position mặc định cho các robot khi không dùng simulation
        """
        default_positions = {
            "robot1": [0.5, -0.6928, 0.8],
            "robot2": [1.4, 0.6, 0.8],
            "robot3": [-0.3, 0.6928, 0.8],
        }

        for agent_name in self.agent_names:
            if agent_name in default_positions:
                self.agent_config[agent_name]["position"] = default_positions[agent_name]
            else:
                # Position mặc định cho robot mới
                self.agent_config[agent_name]["position"] = [0.0, 0.0, 0.8]

            print(f"[INFO] {agent_name}: Default position={self.agent_config[agent_name]['position']}")

    def _update_robot_positions(self):
        """
        Lấy position của các robot từ PyBullet simulation
        và cập nhật vào agent_config
        """
        for agent_name in self.agent_names:
            if agent_name in self.env.robot_id:
                robot = self.env.robot_id[agent_name]
                # Lấy vị trí base của robot từ PyBullet
                base_pos, base_orn = p.getBasePositionAndOrientation(robot.id)
                # Lấy vị trí end-effector (tay robot)
                ee_pos = robot.get_joint_obs()[:3]  # x, y, z của end-effector

                # Cập nhật position vào config (dùng end-effector position)
                self.agent_config[agent_name]["position"] = list(ee_pos)

                print(f"[INFO] {agent_name}: Base={base_pos}, End-effector={ee_pos}")

    def reachability_analysis(self, objects):
        """
        Phân tích object nào gần agent nào nhất
        """
        agent_objects = {agent: [] for agent in self.agent_names}

        for obj_name, obj_data in objects.items():
            # Xử lý 2 trường hợp: obj_data là tuple (x,y,z) hoặc là object ID
            if isinstance(obj_data, tuple):
                # Trường hợp objects là dict với position cứng
                obj_pos = obj_data
            elif isinstance(obj_data, int):
                # Trường hợp objects là dict với PyBullet object IDs
                try:
                    obj_pos, _ = p.getBasePositionAndOrientation(obj_data)
                except:
                    continue
            else:
                continue

            # Tính khoảng cách từ object đến tất cả agents
            distances = {}
            for agent_name, agent_info in self.agent_config.items():
                agent_pos = agent_info["position"]
                distances[agent_name] = math.dist(obj_pos, agent_pos)

            # Tìm agent gần nhất
            closest_agent = min(distances, key=distances.get)
            agent_objects[closest_agent].append(obj_name)

        return agent_objects

    def _generate_handoff_labels(self):
        """
        Tự động generate tất cả các label handoff có thể (agentX_to_agentY)

        Returns:
            Set of valid handoff labels
        """
        handoff_labels = set()
        for agent1 in self.agent_names:
            for agent2 in self.agent_names:
                if agent1 != agent2:
                    handoff_labels.add(f"{agent1}to{agent2}")
        return handoff_labels

    def _format_reachability_status(self, agent_objects):
        """Format reachability status cho prompt"""
        lines = []
        for agent_name in self.agent_names:
            objects = agent_objects.get(agent_name, [])
            # Capitalize agent name cho display
            display_name = agent_name.upper()
            objects_str = ", ".join(objects) if objects else "None"
            lines.append(f"        {display_name}: {objects_str}")
        return "\n".join(lines)

    def _format_capabilities(self):
        """Format capabilities section cho prompt"""
        lines = []
        for agent_name, agent_info in self.agent_config.items():
            display_name = agent_name.upper()
            capabilities = agent_info["capabilities"]
            lines.append(f"        {display_name}: {capabilities}")
        return "\n".join(lines)

    def _generate_label_description(self):
        """Generate mô tả về các labels có thể dùng"""
        agent_list = ", ".join(self.agent_names)
        handoff_labels = self._generate_handoff_labels()
        handoff_list = ", ".join(sorted(handoff_labels))

        return f"""<label>: <instruction>
        where <label> ∈ {{ {agent_list}, {handoff_list} }}

        - {agent_list}: describes an action executed by that agent. For example, if {self.agent_names[0]} takes this action, label is {self.agent_names[0]}.
        - {handoff_list}: describes a **move action** between two agents that move to the designated position. This label occurs when the responsible agent for the task cannot directly reach or manipulate the object due to reachability or capability limitations, so another agent must deliver the object via a handover. For example, when the task requires an object that agent A cannot reach but agent B can, agent B must pick up the object and move to the designated handover position. The plan will be: ("BtoA": "move object to A")"""

    def _generate_example(self, agent_objects):
        """
        Generate example dựa trên số agents hiện có
        """
        # Lấy 2 agents đầu tiên để làm example
        agents_for_example = self.agent_names[:2] if len(self.agent_names) >= 2 else self.agent_names

        agent1 = agents_for_example[0]
        agent2 = agents_for_example[1] if len(agents_for_example) > 1 else agent1

        # Format reachability cho example
        example_reachability = []
        for agent in agents_for_example:
            objects = agent_objects.get(agent, [])[:2]  # Lấy 2 objects đầu
            objects_str = ", ".join(objects) if objects else "object1, object2"
            example_reachability.append(f"    {agent.upper()}: {objects_str}")

        reachability_str = "\n".join(example_reachability)

        return f"""Here's an example input and response:
    INPUT:
    Task: Clean the table. The fruits should go into the plate. 
    Objects: ["sponge", "lemon", "apple", "plate"], 
    Reachability status: 
{reachability_str}

    RESPONSE: (MUST FOLLOW THE FORMAT)
    ("{agent2}", "pick lemon"),
    ("{agent2}", "place lemon on the plate"),
    ("{agent1}", "pick apple"),
    ("{agent1}to{agent2}", "move apple to {agent2}"),
    ("{agent2}", "pick apple"),
    ("{agent2}", "place apple on the plate"),
    ("{agent1}", "pick sponge"),
    ("{agent1}", "sweep the table"),"""

    def build_prompt(self, task=None):
        # Lấy tên các objects từ environment
        if self.use_simulation:
            object_names = [name for name in self.env.objects.keys()]
        else:
            object_names = list(self.env.objects.keys())

        objects = ", ".join(object_names)

        if task is None:
            task = input("Input task: ")

        # Phân tích reachability dựa trên vị trí thực tế từ simulation
        agent_objects = self.reachability_analysis(self.env.objects)

        # Build các sections của prompt
        reachability_status = self._format_reachability_status(agent_objects)
        capabilities = self._format_capabilities()
        label_description = self._generate_label_description()
        example = self._generate_example(agent_objects)

        prompt_template = f"""
        You are an intelligent collaborative planner capable of coordinating multiple agents based on their manipulation capabilities and reachable workspaces.
    Your mission is to perform task planning for {len(self.agent_names)} agents ({', '.join(self.agent_names)}), given the environment description and an overall task goal.

    Environment description:
    1) Task: "{task}"
    2) Objects: {objects}
    3) Reachability status: 
{reachability_status}

    Capabilities:
{capabilities}

    You must follow the following criteria:
    1) Each step of the task plan must follow this syntax:
         {label_description}

    2) Every "place" action must be preceded by a corresponding "pick" action of the same object. This ensures that the agent actually has the object in hand before placing it into the destination. After the "place" action is executed, the object is no longer in the agent's hand.

    3) If an object is not reachable by the agent responsible for the task, a "move" action must be included to transfer the object from another agent who can reach it. This ensures that the object is physically accessible before any manipulation actions are attempted.

    4) Prioritize actions that an agent can complete independently, without requiring handover. Execute these actions first to allow agents to work in parallel. Schedule handover actions only after all independent tasks in the same area are completed.

    5) - A robot must place or transfer the object it is holding before picking another one.
        - Each object can only be held by one robot at a time (no conflicts).
        - The sequence must be logical and executable step by step without skipping.

    6) Output ONLY the task plan. Do not add any explanation, commentary, or extra text.

    7) Minimize total completion time by: 
        - Balancing workload across all agents - avoid one agent being overloaded while others are idle.
        - Scheduling handovers to minimize idle time.
        - Maximizing parallel execution where possible.

    {example}
    """

        return prompt_template

    def print_agent_summary(self):
        print("\n" + "=" * 60)
        print(" AGENT CONFIGURATION SUMMARY")
        print("=" * 60)

        for agent_name, agent_info in self.agent_config.items():
            print(f"\n{agent_name.upper()}:")
            print(f"  Position: {agent_info['position']}")
            print(f"  Capabilities: {agent_info['capabilities'][:50]}...")

        print(f"\nTotal agents: {len(self.agent_names)}")
        print(f"Possible handoff combinations: {len(self._generate_handoff_labels())}")
        print("=" * 60 + "\n")

    def cleanup(self):
        """Đóng kết nối PyBullet nếu được tạo bởi PromptBuilder"""
        if self.physics_client is not None:
            try:
                p.disconnect(self.physics_client)
                print("[INFO] PyBullet connection closed")
            except:
                pass

    def __del__(self):
        """Destructor để cleanup khi object bị xóa"""
        self.cleanup()


def build_prompt(task=None, agent_config=None, use_simulation=False):
    """
    Build prompt với option sử dụng simulation hoặc không

    Args:
        task: Task description
        agent_config: Agent configuration
        use_simulation: Nếu True, khởi tạo PyBullet simulation để lấy position thực tế
                       Nếu False (default), dùng position mặc định (nhanh hơn cho LLM calls)
    """
    builder = PromptBuilder(agent_config, use_simulation=use_simulation)
    return builder.build_prompt(task)