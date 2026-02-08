# Human-Robot Collaboration (HRC) Simulation


##  Project Structure

```
HRC/
├── AI_module/              # LLM integration module (Gemini)
│   ├── LLM.py              # Gemini API calls
│   ├── preprocessLLM.py    # Response preprocessing
│   └── process_prompt.py   # Prompt building
│
├── graph/                  # Task plan execution
│   ├── execute_command.py  # RobotExecutor class
│   └── graph_command.py    # Graph generator
│
├── robot/                  # Robot control
│   ├── robot_env.py        # UR5Robotiq85 class
│   ├── robot_action.py     # Pick, place, move actions
│   └── ur5_robotiq_85.urdf # Robot URDF model
│
├── my_objects/             # Object URDFs
│   ├── objects_simu.py     # Dynamic object creation
│   └── [object folders]/   # URDF files for objects
│
├── task_plan_truth/        # Task plan JSON files
│   ├── commands_task_1.json
│   ├── commands_task_2.json
│   └── ...
│
├── Task1/                  # Task 1: Sort cubes (2 robots)
├── Task2/                  # Task 2: Sort cubes (3 robots)
├── Task3/                  # Task 3: Clean table
├── Task4/                  # Task 4: Stack bowls
├── Task5/                  # Task 5: Sort cubes (Sequential)
│
├── paths.py                # URDF file paths
├── requirements.txt        # Dependencies
└── README.md
```

---

##  Installation

### 1. Clone repository

```bash
git clone https://github.com/thanhnguyencanh/LLM_DAG4MultiRobot.git
cd LLM_DAG4MultiRobot
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Running Tasks

```bash
# Run from project root directory
cd /path/to/HLLM_DAG4MultiRobot

#Modify your LLM API in AI_module/LLM.py

#Before run task, modify task in graph/execute_command

# Task 1: Sort cubes with 2 robots
python Task1/main.py

# Task 2: Sort cubes with 3 robots
python Task2/main.py

# Task 3: Clean table
python Task3/main.py

# Task 4: Stack bowls
python Task4/main.py

# Task 5: Sort cubes ( sequential)
python Task5/main.py
```

---


### Important: Update import in `execute_command.py`

When switching between Tasks, you need to **change the import line** in `graph/execute_command.py`:

```python
# Line 6 in graph/execute_command.py

# For Task 1:
from Task1.environment import Environment

# For Task 2:
from Task2.environment import Environment

# For Task 3:
from Task3.environment import Environment

# For Task 4:
from Task4.environment import Environment

# For Task 5:
from Task5.environment import Environment
```

