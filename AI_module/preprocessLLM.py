def preprocess_llm_response(llm_response):
    lines = []

    for line in llm_response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        agent = None
        action = None
        node_str = "node[]"  # default

        # Tuple format with optional node: (robot1, pick cube, node[...])
        if line.startswith('(') or line.startswith('['):
            line_clean = line.strip('()[]')
            parts = line_clean.split(',', 2)  # up to 3 parts
            if len(parts) >= 2:
                agent = parts[0].strip().lower()
                action = parts[1].strip()
                if len(parts) == 3:
                    node_str = parts[2].strip()

        # Colon format: robot2: PICK apple
        elif ':' in line:
            parts = line.split(':', 1)
            agent = parts[0].strip().lower()
            action = parts[1].strip()
        # Comma separated: robot1, pick cube
        elif ',' in line:
            parts = line.split(',', 1)
            agent = parts[0].strip().lower()
            action = parts[1].strip()
        # Space separated: robot1 pick cube
        else:
            parts = line.split(None, 1)
            if len(parts) == 2:
                agent = parts[0].strip().lower()
                action = parts[1].strip()

        # Fix PLACE actions
        if action:
            action_fixed = fix_place_action(action)
            if action_fixed:
                # Wrap agent, action, node in quotes
                lines.append(f'("{agent}", "{action_fixed}", "{node_str}"),')

    return '\n'.join(lines)


def fix_place_action(action):
    """
    Fix or validate PLACE actions to ensure proper format.
    """
    action = action.strip()
    if action.lower().startswith('place '):
        parts = action.split()
        if len(parts) >= 4:
            prepositions = ['in', 'on', 'into', 'onto', 'at']
            if any(prep in parts for prep in prepositions):
                return action
            else:
                return f"{parts[0]} {parts[1]} in {' '.join(parts[2:])}"
        elif len(parts) == 3:
            return f"{parts[0]} {parts[1]} in {parts[2]}"
        else:
            return None
    return action
