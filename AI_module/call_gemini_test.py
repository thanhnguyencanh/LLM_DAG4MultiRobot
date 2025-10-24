

def call_gemini_1():
    return[ ("robot2", "pick yellow_cube", "node[]"),
        ("robot2", "place yellow_cube in yellow_bowl", "node[1]"),
        ("robot1", "pick green_cube_2", "node[]"),
        ("robot1", "place green_cube_2 in green_bowl", "node[3]"),
        ("robot1", "pick red_cube", "node[]"),
        ("robot1torobot2", "move red_cube to robot2", "node[5]"),
        ("robot2", "pick red_cube", "node[6]"),
        ("robot2", "place red_cube in red_bowl", "node[7]"),
        ("robot2", "pick green_cube_1", "node[]"),
        ("robot2torobot1", "move green_cube_1 to robot1", "node[9]"),
        ("robot1", "pick green_cube_1", "node[10]"),
        ("robot1", "place green_cube_1 in green_bowl", "node[11]")
        ]
