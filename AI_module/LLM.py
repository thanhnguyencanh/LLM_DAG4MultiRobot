import google.generativeai as genai
from AI_module.process_prompt import build_prompt
import ast
import re
from AI_module.preprocessLLM import preprocess_llm_response


def call_gemini():
    API_KEY = ""  # Replace with your actual API key
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
        # Regex to extract 3 elements, including when 3rd element has commas (like node[4,8])
        pattern = r'\("([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\)'
        matches = re.findall(pattern, text)

        if matches:
            # Return list of tuples (agent, action, node)
            return matches

        # Fallback if Regex fails, use ast.literal_eval line by line
        task_list = []
        for line in text.split('\n'):
            line = line.strip().rstrip(',')
            if not line: continue
            try:
                task_tuple = ast.literal_eval(line)
                if len(task_tuple) == 3:
                    task_list.append(task_tuple)
            except:
                continue
        return task_list

    except Exception as e:
        print(f"Error parsing task plan: {e}")
        return []


def manual_parse_single_line(line):
    # Helper function for manual parsing if ast.literal_eval fails
    try:
        # More flexible regex to extract content between double quotes
        parts = re.findall(r'"([^"]*)"', line)
        if len(parts) >= 3:
            return (parts[0], parts[1], parts[2])
    except:
        pass
    return None


def manual_parse_tasks(text):
    tasks = []
    lines = text.split('\n')
    for line in lines:
        task = manual_parse_single_line(line)
        if task:
            tasks.append(task)
    return tasks