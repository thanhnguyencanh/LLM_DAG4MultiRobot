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

        # Clean, lowercase, format
        if agent and action:
            agent = agent.strip('"\'').lower()
            action = action.strip('"\'').lower()
            lines.append(f'("{agent}", "{action}"),')

    return '\n'.join(lines)


