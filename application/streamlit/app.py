import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from autogen import Agent
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent
import json

DEFAULT_CONFIG = json.load(open('./llm_config.json', 'r'))

ASSISTANT_NAME_DEFAULT = "assistant"
ASSISTANT_SYSTEM_DEFAULT = """你是一个AI助手，使用你的编码和语言技能解决任务，请注意以下几点：
1.你可以编写python代码或shell脚本供用户执行，用户会回复执行结果。
2.不要在一个回答中包含多个代码块，不要要求用户复制并粘贴结果。代码里可以使用 'print' 函数进行输出，检查用户返回的执行结果。
3.如果需要，你可以使用提供给你的functions。
4.整个任务流程执行完毕后，你要回复用户"TERMINATE"以终止任务。"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """如果你认为当前任务已经执行完毕，请回复我"TERMINATE"终止任务，否则请继续执行任务。"""

st.write("""# AutoGen Chat Agents""")


def generate_img(prompt):
    # 定义目标URL和要发送的数据
    return "http://10.139.17.136:7890/test.png"


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
    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            st.markdown(message)
        return super()._process_received_message(message, sender, silent)


selected_model = None
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

DEFAULT_CONFIG.update({'model': selected_model, 'presence_penalty': presence_penalty})
print(DEFAULT_CONFIG)
with st.container():
    # for message in st.session_state["messages"]:
    #    st.markdown(message)

    user_input = st.chat_input("Type something...")
    if user_input:
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
            "config_list": [
                DEFAULT_CONFIG
            ]
        }
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

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define an asynchronous function
        async def initiate_chat():
            await user_proxy.a_initiate_chat(
                assistant,
                message=user_input,
            )

        # Run the asynchronous function within the event loop
        loop.run_until_complete(initiate_chat())
