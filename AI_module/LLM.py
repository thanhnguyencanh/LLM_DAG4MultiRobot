import google.generativeai as genai
from AI_module.process_prompt import build_prompt
import ast
import re
from AI_module.preprocessLLM import preprocess_llm_response


def call_gemini():
    API_KEY = "AIzaSyCkzGKs2xcyQgrQ1hweFV92_XkPrutCFEc"
    genai.configure(api_key=API_KEY)

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = build_prompt()
    response = model.generate_content(prompt)

    response_text = response.text
    print("Raw LLM Response:", response_text)

    preprocessed_response = preprocess_llm_response(response_text)
    print("Preprocessed LLM Response:", preprocessed_response)

    return parse_task_plan(preprocessed_response)


def parse_task_plan(text):
    try:
        pattern = r'\("([^"]+)",\s*"([^"]+)"\)'
        matches = re.findall(pattern, text)

        if matches:
            return matches

        lines = text.split('\n')
        task_list = []

        for line in lines:
            line = line.strip()
            if line.startswith('(') and line.endswith('),'):
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

        return manual_parse_tasks(text)

    except Exception as e:
        print(f"Error parsing task plan: {e}")
        return []


def manual_parse_tasks(text):
    tasks = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if '("' in line and '")' in line:
            parts = line.split('("')[1].split('")')[0]
            if '", "' in parts:
                agent, action = parts.split('", "')
                tasks.append((agent, action))

    return tasks