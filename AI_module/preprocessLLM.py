import re


def preprocess_llm_response(llm_response):
    lines = []
    # Regex pattern to find tuple structure ("...", "...", "...") precisely
    # It captures 3 groups of content within double quotes
    tuple_pattern = re.compile(r'\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)')

    for line in llm_response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Try to find standard Tuple format (agent, action, node)
        match = tuple_pattern.search(line)

        if match:
            agent = match.group(1).lower()
            action = match.group(2)
            node_str = match.group(3)

            action_fixed = fix_place_action(action)
            if action_fixed:
                # Repack into standard format
                lines.append(f'("{agent}", "{action_fixed}", "{node_str}")')

        # If not tuple format, handle legacy formats (fallback)
        elif ':' in line:
            parts = line.split(':', 1)
            agent = parts[0].strip().strip('"\'').lower()
            action = parts[1].strip().strip('"\'')
            lines.append(f'("{agent}", "{fix_place_action(action)}", "node[]")')

    return ',\n'.join(lines)

def fix_place_action(action):
    action = action.strip()
    if action.lower().startswith('place '):
        parts = action.split()
        prepositions = ['in', 'on', 'into', 'onto', 'at']
        if not any(prep in parts for prep in prepositions):
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} in {' '.join(parts[2:])}"
            elif len(parts) == 2:
                return action
    return action