import google.generativeai as genai
from AI_module.process_prompt import build_prompt
import ast
import re


def call_gemini():
    API_KEY = "AIzaSyCkzGKs2xcyQgrQ1hweFV92_XkPrutCFEc"
    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = build_prompt()
    response = model.generate_content(prompt)
    print(response.text)

    # Parse the response text to extract tuples
    return parse_task_plan(response.text)


def parse_task_plan(text):
    """Parse the text response from Gemini to extract task plan tuples"""
    try:
        # Method 1: Try to extract tuples using regex
        pattern = r'\("([^"]+)",\s*"([^"]+)"\)'
        matches = re.findall(pattern, text)

        if matches:
            return matches

        # Method 2: Try to evaluate as Python literal (more risky but handles complex cases)
        # Find lines that look like tuples
        lines = text.split('\n')
        task_list = []

        for line in lines:
            line = line.strip()
            if line.startswith('(') and line.endswith('),'):
                # Remove trailing comma
                line = line[:-1]
                try:
                    # Safely evaluate the tuple
                    task_tuple = ast.literal_eval(line)
                    if len(task_tuple) == 2:
                        task_list.append(task_tuple)
                except:
                    continue
            elif line.startswith('(') and line.endswith(')'):
                try:
                    task_tuple = ast.literal_eval(line)
                    if len(task_tuple) == 2:
                        task_list.append(task_tuple)
                except:
                    continue

        if task_list:
            return task_list

        # Method 3: Manual parsing as fallback
        return manual_parse_tasks(text)

    except Exception as e:
        print(f"Error parsing task plan: {e}")
        return []


def manual_parse_tasks(text):
    """Manual parsing as fallback method"""
    tasks = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if '("' in line and '")' in line:
            # Extract content between quotes
            parts = line.split('("')[1].split('")')[0]
            if '", "' in parts:
                agent, action = parts.split('", "')
                tasks.append((agent, action))

    return tasks