

def call_gemini_1():
    return[ ("robot2", "PICK yellow_cube", "node[]"),
        ("robot2", "PLACE yellow_cube into yellow_bowl", "node[1]"),
        ("robot1", "PICK green_cube_2", "node[]"),
        ("robot1", "PLACE green_cube_2 into green_bowl", "node[3]"),
        ("robot1", "PICK red_cube", "node[]"),
        ("robot1torobot2", "MOVE red_cube to robot2", "node[5]"),
        ("robot2", "PICK red_cube", "node[6]"),
        ("robot2", "PLACE red_cube into red_bowl", "node[7]"),
        ("robot2", "PICK green_cube_1", "node[]"),
        ("robot2torobot1", "MOVE green_cube_1 to robot1", "node[9]"),
        ("robot1", "PICK green_cube_1", "node[10]"),
        ("robot1", "PLACE green_cube_1 into green_bowl", "node[11]")
        ]

def call_gemini_2():
            return   [
    ("robot1", "pick green_cube_1", "node[]"),
    ("robot2", "pick yellow_cube_1", "node[]"),
    ("robot3", "pick red_cube_1", "node[]"),
    ("robot1", "pick green_cube_2", "node[]"),
    ("robot1", "pick yellow_cube_2", "node[]"),
    ("robot2", "pick red_cube_2", "node[]"),
    ("robot3", "pick green_cube_3", "node[]"),
    ("robot1", "place green_cube_1 in green_bowl", "node[1]"),
    ("robot2", "place yellow_cube_1 in yellow_bowl", "node[2]"),
    ("robot3", "place red_cube_1 in red_bowl", "node[3]"),
    ("robot1", "place green_cube_2 in green_bowl", "node[4]"),
    ("robot1torobot2", "move yellow_cube_2 to robot2", "node[5]"),
    ("robot2torobot3", "move red_cube_2 to robot3", "node[6]"),
    ("robot3torobot1", "move green_cube_3 to robot1", "node[7]"),
    ("robot2", "pick yellow_cube_2", "node[12]"),
    ("robot3", "pick red_cube_2", "node[13]"),
    ("robot1", "pick green_cube_3", "node[14]"),
    ("robot2", "place yellow_cube_2 in yellow_bowl", "node[15]"),
    ("robot3", "place red_cube_2 in red_bowl", "node[16]"),
    ("robot1", "place green_cube_3 in green_bowl", "node[17]")
    ]


def call_gemini_3():
        return [
    ("robot1", "pick banana", "node[]"),
    ("robot1", "place banana on plate", "node[1]"),
    ("robot2", "pick spoon", "node[]"),
    ("robot2", "place spoon into drawer", "node[3]"),
    ("robot2", "pick purple_cup", "node[]"),
    ("robot2", "place purple_cup into drawer", "node[5]"),
    ("robot2", "pick apple", "node[]"),
    ("robot2torobot1", "move apple to robot1", "node[7]"),
    ("robot1", "pick apple", "node[8]"),
    ("robot1", "place apple on plate", "node[9]"),
    ("robot1", "pick orange_cup", "node[]"),
    ("robot1torobot2", "move orange_cup to robot2", "node[11]"),
    ("robot2", "pick orange_cup", "node[12]"),
    ("robot2", "place orange_cup into drawer", "node[13]")
                ]


def call_gemini_4():
    return [
        ("robot1", "pick apple", "node[]"),
        
        ("robot1", "place apple in the box", "node[1]"),
    
        ("robot2", "pick banana", "node[]"),
    
        ("robot2", "place banana in the box", "node[3, 2]"),

        ("robot2", "pick cup", "node[4]"),
        
        ("robot2", "place cup in the box", "node[5]")
    ]

def call_gemini_5():
    return [
        ("robot2", "pick red_cube", "node[]"),
        ("robot2torobot1", "move red_cube to robot1", "node[1]"),
        ("robot1", "pick red_cube", "node[2]"),
        ("robot2", "pick yellow_cube", "node[]"),
        ("robot1", "place red_cube into red_bowl", "node[3]"),
        ("robot2torobot1", "move yellow_cube to robot1", "node[4]"),
        ("robot1", "pick yellow_cube", "node[6]"),
        ("robot2", "pick green_cube", "node[]"),
        ("robot1", "place yellow_cube into yellow_bowl", "node[7]"),
        ("robot2torobot1", "move green_cube to robot1", "node[8]"),
        ("robot1", "pick green_cube", "node[10]"),
        ("robot1", "place green_cube into green_bowl", "node[11]")
    ]