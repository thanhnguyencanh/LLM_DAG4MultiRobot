def preprocess_llm_response(llm_response):
    lines = []

    for line in llm_response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        agent = None
        action = None

        # Colon format: robot2: PICK apple
        if ':' in line:
            parts = line.split(':', 1)
            agent = parts[0].strip()
            action = parts[1].strip()

        # Bracket format: (robot1, pick cube) or [robot1, pick cube]
        elif line.startswith('(') or line.startswith('['):
            line_clean = line.strip('()[]')
            parts = line_clean.split(',', 1)
            if len(parts) == 2:
                agent = parts[0].strip()
                action = parts[1].strip()

        # Comma separated: robot1, pick cube
        elif ',' in line:
            parts = line.split(',', 1)
            agent = parts[0].strip()
            action = parts[1].strip()

        # Space separated: robot1 pick cube
        else:
            parts = line.split(None, 1)
            if len(parts) == 2:
                agent = parts[0].strip()
                action = parts[1].strip()

        # Clean and validate
        if agent and action:
            agent = agent.strip('"\'').lower()
            action_original = action.strip('"\'').lower()

            # Fix common PLACE action errors
            action_fixed = fix_place_action(action_original)

            if action_fixed:  # Only add if action is valid/fixable
                lines.append(f'("{agent}", "{action_fixed}"),')

    return '\n'.join(lines)


def fix_place_action(action):
    """
    Fix or validate PLACE actions to ensure they have proper format.
    Valid: PLACE object IN/ON location
    Invalid: PLACE object location (missing preposition)
    """
    action = action.strip()

    # Check if it's a PLACE action
    if action.startswith('place '):
        parts = action.split()

        # Valid PLACE should have at least 4 parts: PLACE object IN/ON location
        if len(parts) >= 4:
            # Check if there's a preposition (in, on, into, onto)
            prepositions = ['in', 'on', 'into', 'onto', 'at']
            has_preposition = any(prep in parts for prep in prepositions)

            if has_preposition:
                return action  # Valid
            else:
                # Missing preposition - try to fix by inserting "in"
                # PLACE red_cube red_bowl -> PLACE red_cube in red_bowl
                return f"{parts[0]} {parts[1]} in {' '.join(parts[2:])}"

        elif len(parts) == 3:
            # PLACE object location - add "in" preposition
            return f"{parts[0]} {parts[1]} in {parts[2]}"
        else:
            # Too few parts, invalid
            return None

    return action