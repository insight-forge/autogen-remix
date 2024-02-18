from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, Set
import os, json, logging, re, requests
import streamlit

Scene = {}

_basedir = os.path.dirname(os.path.abspath(__file__))
for dir in os.listdir(_basedir):
    if dir.startswith("Scene_"):
        with open(os.path.join(_basedir, dir), mode="r", encoding="utf-8") as py_file:
            py_code = py_file.read()

        output = {}
        exec(py_code, {"__name__": "__main__"}, output)
        for scene in output.keys():
            Scene[f"{scene} | { output[scene]['scenario_overview']}"] = output[scene]


def system_message_visualize(system: str, st: streamlit):
    side_markdown = "<span style='color:red;'>system message:  \n</span>" + system.replace("\n", "  \n")
    st.session_state.side_markdown = side_markdown
    with st.sidebar:
        st.markdown(side_markdown, unsafe_allow_html=True)
    st.session_state.messages.append({'role': 'system', 'content': system})


def config_list_from_json(
        env_or_file: str,
        file_location: Optional[str] = ""
) -> List[Dict]:
    json_str = os.environ.get(env_or_file)
    if json_str:
        config_list = json.loads(json_str)
    else:
        config_list_path = os.path.join(file_location, env_or_file)
        try:
            with open(config_list_path) as json_file:
                config_list = json.load(json_file)
        except FileNotFoundError:
            logging.warning(f"The specified config_list file '{config_list_path}' does not exist.")
            return []
    return config_list


def _format_json_str(jstr):
    result = []
    inside_quotes = False
    last_char = " "
    for char in jstr:
        if last_char != "\\" and char == '"':
            inside_quotes = not inside_quotes
        last_char = char
        if not inside_quotes and char == "\n":
            continue
        if inside_quotes and char in ("\n", "\t"):
            char = "\\" + char
        result.append(char)
    return "".join(result)


def execute_function(func_call, _function_map) -> Dict[str, str]:
    func_name = func_call.get("name", "")
    func = _function_map.get(func_name, None)

    is_exec_success = False
    if func is not None:
        # Extract arguments from a json-like string and put it into a dict.
        input_string = _format_json_str(func_call.get("arguments", "{}"))
        try:
            arguments = json.loads(input_string)
        except json.JSONDecodeError as e:
            arguments = None
            content = f"Error: {e}\n You argument should follow json format."

        # Try to execute the function
        if arguments is not None:
            try:
                content = func(**arguments)
                is_exec_success = True
            except Exception as e:
                content = f"Error: {e}"
    else:
        content = f"Error: Function {func_name} not found."

    return {
        "name": func_name,
        "role": "function",
        "content": str(content),
    }

def get_wenxin_access_token(api_key, secret_key):
    url = "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}".format(**{'api_key': api_key, 'secret_key': secret_key})

    payload = json.dumps("")
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json().get("access_token")