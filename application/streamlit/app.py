import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import time
import requests
from IPython import get_ipython
import autogen
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = "{the dir path of the config file}"
CONFIG_FILENAME = "OAI_CONFIG_LIST"
################################################################################################

ASSISTANT_NAME_DEFAULT = "assistant"
ASSISTANT_SYSTEM_DEFAULT = """你是一个AI助手，使用你的编码和语言技能和代理一起解决任务，请注意以下几点：
1.与你对话的是代理，他具有和人类交互、执行Python代码或shell脚本、执行function等功能。
1.你可以编写python代码或shell脚本供其他代理执行，与你对话的代理会回复执行结果。
2.代理仅可执行一个代码块，所以不要在一个回答中包含多个代码块，不要要求代理复制并粘贴结果。代码里可以使用 'print' 函数进行输出，检查代理返回的执行结果。
3.如果需要，你可以使用提供给你的functions。
4.如果你认为任务执行完毕，或者需要人工介入，你可以在最后回复"TERMINATE"以终止和代理的交互。"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """如果你认为任务已经执行完毕或者需要人工介入，请回复"TERMINATE"终止任务，否则请继续执行任务。"""

st.write("""# Character Chat""")


class TrackableAssistantAgent(CharacterAssistantAgent):
    def _process_received_message(self, message, sender, silent):
        if isinstance(message, Dict) and "name" in message:
            st.session_state.messages.append(message)
        else:
            st.session_state.messages.append({"role": sender.name, "content": message})

        with st.chat_message(sender.name):
            if isinstance(message, Dict) and 'name' in message:
                if message['name'].startswith('image_'):
                    st.image(message['content'], width=350)
                else:
                    st.markdown(message['content'])
            else:
                st.markdown(message)
        return super()._process_received_message(message, sender, silent)


class TrackableUserProxyAgent(CharacterUserProxyAgent):

    def __init__(
            self,
            name: str,
            llm_config: Optional[Union[Dict, bool]] = False,
            is_termination_msg: Optional[Callable[[Dict], bool]] = None,
            max_consecutive_auto_reply: Optional[int] = None,
            human_input_mode: Optional[str] = "NEVER",
            code_execution_config: Optional[Union[Dict, bool]] = None,
            **kwargs,
    ):
        super().__init__(
            name,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            llm_config=llm_config,
            code_execution_config=code_execution_config,
            **kwargs,
        )

    def _process_received_message(self, message, sender, silent):
        if isinstance(message, Dict) and "function_call" in message:
            st.session_state.messages.append(message)
        else:
            st.session_state.messages.append({"role": sender.name, "content": message})

        with st.chat_message(sender.name):
            if isinstance(message, Dict) and "function_call" in message:
                st.markdown(message["function_call"])
            else:
                st.markdown(message)
        return super()._process_received_message(message, sender, silent)

    def get_human_input(self, prompt):

        return "exit"

    def initiate_chat(
            self,
            recipient: "ConversableAgent",
            clear_history: Optional[bool] = True,
            history: Optional[List] = None,
            silent: Optional[bool] = False,
            **context,
    ):

        self._prepare_chat(recipient, clear_history)

        for message in history:
            if "function_call" in message or "name" in message:
                recipient._oai_messages[self].append(message)
                self._oai_messages[recipient].append(message)
            else:
                recipient._oai_messages[self].append({'role': message['role'], 'content': message['content']})
                if message['role'] == 'user':
                    self._oai_messages[recipient].append({'role': 'assistant', 'content': message['content']})
                else:
                    self._oai_messages[recipient].append({'role': 'user', 'content': message['content']})

        self.send(self.generate_init_message(**context), recipient, silent=silent)


def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-3.5-turbo', 'gpt-4'], index=0)
        presence_penalty = st.slider("presence_penalty：", -2.0, 2.0, 0.7, 0.1)

        with st.expander("AssistantAgent", False):
            assistant_name = st.text_input('name', value=ASSISTANT_NAME_DEFAULT)
            assistant_system = st.text_area('system message', value=ASSISTANT_SYSTEM_DEFAULT)

        with st.expander("UserProxyAgent", False):
            userproxy_name = st.text_input('name', value=USERPROXY_NAME_DEFAULT)
            human_input_mode = st.selectbox('human input mode', ['NEVER', 'TERMINATE', 'ALLWAYS'], index=1)
            userproxy_auto_reply = st.text_area('auto reply', value=USERPROXY_AUTO_REPLY_DEFAULT)

    # update llm_config
    config_list = autogen.config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME,
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-4",
            }
        })
    config_list = [item.update({'presence_penalty': presence_penalty}) or item for item in config_list if
                   item['model'] == selected_model]
    llm_config = {
        "functions": [
            {
                "name": "image_generate",
                "description": "generate a image by prompting if the user's intention is to generate an image",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "prompt for generating image. Please note that prompt only supports English",
                        }
                    },
                    "required": ["prompt"],
                },
            },
                {
                    "name": "python",
                    "description": "run cell in ipython and return the execution result.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Valid Python cell to execute.",
                            }
                        },
                        "required": ["code"],
                    },
                },
                          ],
        "request_timeout": 600,
        "config_list": config_list
    }
    print(llm_config)

    # create an AssistantAgent instance named "assistant"
    assistant = TrackableAssistantAgent(
        name=assistant_name,
        system_message=assistant_system,
        llm_config=llm_config)

    # create a UserProxyAgent instance named "user"
    user_proxy = TrackableUserProxyAgent(
        name=userproxy_name,
        default_auto_reply=userproxy_auto_reply,
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode=human_input_mode,
        code_execution_config={'work_dir': 'coding'})
    #define all fucntion
    def generate_img(prompt):
        # 定义目标URL和要发送的数据
        url = "http://10.139.17.136:8089/sd_gen"
        data = {"prompt": prompt}
        response = requests.post(url, data=data)
        return response.text

    def exec_python(code):
        return user_proxy.execute_code_blocks([("python", code)])

    user_proxy.register_function(
        function_map={
            "image_generate": generate_img,
             "python":exec_python
        }
    )

    # streamlit ui start
    if "messages" not in st.session_state:
        st.session_state.messages = []
    print(st.session_state.messages)
    for message in st.session_state.messages:
        if "function_call" in message:
            message['content'] = None
            st.markdown(message["function_call"])
        elif "name" in message:
            if message['name'].startswith('image_'):
                st.image(message['content'], width=350)
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if user_input := st.chat_input("Type something...", key="prompt"):
        # Define an asynchronous function
        async def initiate_chat():
            user_proxy.initiate_chat(
                assistant,
                message=user_input,
                history=st.session_state.messages,
                clear_history=False
            )

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Run the asynchronous function within the event loop
        loop.run_until_complete(initiate_chat())


if __name__ == "__main__":
    main()