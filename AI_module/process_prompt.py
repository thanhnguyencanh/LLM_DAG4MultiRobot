from Task4.environment import Environment

AGENT_CONFIG = {
    "robot1": {
        "capabilities": """- PICK(object): move to object and pick up
            - MOVE(location): move hand/base to location
            - PLACE(object, destination): place held object into/onto destination
            - SWEEP(surface, tool): wipe/clean a surface using held object""",
    },
    "robot2": {
        "capabilities": """- PICK(object): move to object and pick up
        - MOVE(location): move hand/base to location
        - PLACE(object, destination): place held object into/onto destination
        - SWEEP(surface, tool): wipe/clean a surface using held object""",
    },
}


class PromptBuilder:
    def __init__(self, agent_config=None):
        self.agent_config = agent_config or AGENT_CONFIG
        self.env = Environment()
        self.agent_names = list(self.agent_config.keys())
        self._load_positions_from_environment()

    def _load_positions_from_environment(self):
        if hasattr(self.env, 'agent_positions'):
            for agent_name in self.agent_names:
                if agent_name in self.env.agent_positions:
                    self.agent_config[agent_name]["position"] = self.env.agent_positions[agent_name]
                else:
                    raise ValueError(f"Agent '{agent_name}' position not found in Environment.agent_positions")
            print("[INFO] Loaded agent positions from Environment")
        else:
            raise AttributeError("Environment does not have 'agent_positions' attribute")

        if hasattr(self.env, 'handoff_points'):
            self.handoff_points = self.env.handoff_points
            print("[INFO] Loaded handoff points from Environment")
        else:
            raise AttributeError("Environment does not have 'handoff_points' attribute")

    def get_handoff_point(self, agent1, agent2):
        """
        Lấy handoff point giữa hai robot

        Args:
            agent1: Robot sẽ gửi object
            agent2: Robot sẽ nhận object

        Returns:
            List [x, y, z] của handoff point
        """
        key = f"{agent1}to{agent2}"
        if key in self.handoff_points:
            return self.handoff_points[key]
        else:
            raise KeyError(f"Handoff point '{key}' not found in Environment.handoff_points")

    def get_all_handoff_points(self):
        """
        Lấy tất cả handoff points

        Returns:
            Dict {handoff_label: [x, y, z]}
        """
        return self.handoff_points.copy()

    def reachability_analysis(self, objects):
        """
        Phân tích object nào gần agent nào nhất
        """
        import math

        agent_objects = {agent: [] for agent in self.agent_names}

        for obj_name, obj_pos in objects.items():
            # obj_pos là tuple (x, y, z)
            if not isinstance(obj_pos, tuple) or len(obj_pos) < 3:
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
        agents_for_example = self.agent_names[:2] if len(self.agent_names) >= 2 else self.agent_names

        agent1 = agents_for_example[0]
        agent2 = agents_for_example[1] if len(agents_for_example) > 1 else agent1

        example_reachability = []
        for agent in agents_for_example:
            objects = agent_objects.get(agent, [])[:2]
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
        """Build prompt dựa trên Environment"""
        if task is None:
            task = input("Input task: ")

        # Lấy tên các objects từ environment
        object_names = [name for name in self.env.objects.keys()]
        objects = ", ".join(object_names)

        # Phân tích reachability dựa trên vị trí từ environment
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
        """In ra tóm tắt cấu hình agents và handoff points"""
        print("\n" + "=" * 60)
        print(" AGENT CONFIGURATION SUMMARY")
        print("=" * 60)

        for agent_name, agent_info in self.agent_config.items():
            print(f"\n{agent_name.upper()}:")
            print(f"  Position: {agent_info['position']}")
            print(f"  Capabilities: {agent_info['capabilities'][:50]}...")

        print(f"\nTotal agents: {len(self.agent_names)}")
        print(f"Possible handoff combinations: {len(self._generate_handoff_labels())}")

        print(f"\nHandoff Points:")
        for handoff_label, handoff_pos in sorted(self.handoff_points.items()):
            print(f"  {handoff_label}: {handoff_pos}")

        print("=" * 60 + "\n")


def build_prompt(task=None, agent_config=None):
    """
    Build prompt từ Environment

    Args:
        task: Task description
        agent_config: Agent configuration (nếu None dùng AGENT_CONFIG mặc định)

    Returns:
        Prompt string cho LLM
    """
    builder = PromptBuilder(agent_config)
    return builder.build_prompt(task)