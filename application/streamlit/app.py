import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import time
import requests

import autogen
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = "{the dir path of the config file}"
CONFIG_FILENAME = "OAI_CONFIG_LIST"
################################################################################################

ASSISTANT_NAME_DEFAULT = "assistant"
ASSISTANT_SYSTEM_DEFAULT = """你是一个AI助手，使用你的编码和语言技能解决任务，请注意以下几点：
1.你可以编写python代码或shell脚本供用户执行，用户会回复执行结果。
2.不要在一个回答中包含多个代码块，不要要求用户复制并粘贴结果。代码里可以使用 'print' 函数进行输出，检查用户返回的执行结果。
3.如果需要，你可以使用提供给你的functions。
4.整个任务流程执行完毕后，你要回复用户"TERMINATE"以终止任务。"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """如果你认为当前任务已经执行完毕，请回复我"TERMINATE"终止任务，否则请继续执行任务。"""

st.set_page_config(
        "Character Chat",
        initial_sidebar_state="collapsed",
    )
st.write("""# Character Chat""")

def generate_img(prompt):
    # 定义目标URL和要发送的数据
    url = "http://10.139.17.136:8089/sd_gen"
    data = {"prompt": prompt}
    response = requests.post(url, data=data)
    return response.text


class TrackableAssistantAgent(CharacterAssistantAgent):
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            if isinstance(message, Dict) and 'name' in message:
                if message['name'].startswith('image_'):
                    st.image(message['content'], width=350)
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
            code_execution_config: Optional[Union[Dict, bool]] = False,
            **kwargs,
    ):
        super().__init__(
            name,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            **kwargs,
        )

        self.input_text = None
        self.is_done = True

    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)

    def get_human_input(self, prompt):
        while self.input_text is None:
            time.sleep(1)

        reply = self.input_text
        self.input_text = None
        return reply

    async def a_initiate_chat(
            self,
            recipient: "ConversableAgent",
            clear_history: Optional[bool] = True,
            silent: Optional[bool] = False,
            **context,
    ):
        self.is_done = False
        await super().a_initiate_chat(recipient, clear_history, silent, **context)
        self.is_done = True


with st.sidebar:
    st.header("OpenAI Configuration")
    selected_model = st.selectbox("Model", ['gpt-3.5-turbo'], index=0)
    presence_penalty = st.slider("presence_penalty：", -2.0, 2.0, 0.6, 0.1)

    with st.expander("AssistantAgent", False):
        assistant_name = st.text_input('name', value=ASSISTANT_NAME_DEFAULT)
        assistant_system = st.text_area('system message', value=ASSISTANT_SYSTEM_DEFAULT)

    with st.expander("UserProxyAgent", False):
        userproxy_name = st.text_input('name', value=USERPROXY_NAME_DEFAULT)
        human_input_mode = st.selectbox('human input mode', ['NEVER', 'TERMINATE', 'ALLWAYS'], index=1)
        userproxy_auto_reply = st.text_area('auto reply', value=USERPROXY_AUTO_REPLY_DEFAULT)

config_list = autogen.config_list_from_json(
    file_location=CONFIG_PATH,
    env_or_file=CONFIG_FILENAME,
    filter_dict={
        "model": {
            "gpt-3.5-turbo",
            # "gpt-4",
            # selected_model,
        }
    })
config_list = [item.update({'presence_penalty': presence_penalty}) or item for item in config_list if
               item['model'] == selected_model]

llm_config = {
            "functions": [
                {
                    "name": "image_generate",
                    "description": "generate a image by prompting",
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
    human_input_mode=human_input_mode)

user_proxy.register_function(
    function_map={
        "image_generate": generate_img
    }
)

with st.container():
    # for message in st.session_state["messages"]:
    #    st.markdown(message)

    if user_input := st.chat_input("Type something...", key="prompt"):
        if not user_proxy.is_done:
            user_proxy.input_text = user_input

        if user_proxy.is_done:
            # Define an asynchronous function
            async def initiate_chat():
                user_proxy.initiate_chat(
                    assistant,
                    message=user_input,
                )

            # Create an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Run the asynchronous function within the event loop
            loop.run_until_complete(initiate_chat())
