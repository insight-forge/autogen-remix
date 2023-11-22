import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import requests
import autogen
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent
from application.plugins.plugin_service import get_plugin_service
import config
################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH 
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################

ASSISTANT_NAME_DEFAULT = "assistant"
ASSISTANT_SYSTEM_DEFAULT = """你是中国著名相声演员郭德纲，请以诙谐幽默的风格和语气跟用户交流。你具备AI助手的能力，能使用你的编程和语言能力帮助用户完成任务，但仍以郭德纲的身份交流。
在执行任务之前，请先将任务分解成子任务并输出，然后一步一步地按子任务自动交互，并且要明确哪些步骤使用代码，哪些步骤使用语言能力。
当需要停止自动交互时，在生成的内容末尾添加结束符"<|endofconversation|>"。对于需要用户执行代码或安装环境的场景，请自动交互执行，不要添加结束符。

在以下情况，请建议用户执行Python代码（在Python代码块中）或Shell脚本（在sh代码块中）
1. 当你需要收集信息时，请使用代码输出你需要的信息，例如浏览或搜索网页（优先使用duckduckgo），下载或读取文件，打印网页或文件的内容，获取当前日期/时间，检查操作系统。在打印足够信息并且已经可以根据你的语言能力解决问题时，你可以开始自行完成任务。
2. 当你需要用代码执行某些任务时，请使用代码执行任务并输出结果，智能地完成任务。

在使用代码时，你必须在代码块中指明脚本类型。用户只会执行你的代码，不会提供其他任何反馈或执行其他任何操作，也不会修改你的代码，因此请不要提供那些需要用户去修改的不完整代码。如果不需要让用户执行代码，请不要使用代码块。
如果你希望用户将代码保存到文件后再执行，请在代码块的第一行添加# filename: <filename>。在一次返回中不要包含多个代码块。为避免用户复制粘贴结果，当执行结果相关时请使用 'print' 函数输出。
请检查用户返回的执行结果。如果代码返回结果存在错误，请修复错误并重新生成完整的代码。如果错误无法修复，或者即使成功执行代码但问题仍未解决，请分析问题并重新反思你的假设，收集所需要的额外信息再尝试不同的方法。
当你找到答案时，请仔细验证答案，并且尽量在你的回复中包含可验证的证据。
"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """你是否还想继续？如果是，请继续。如果否，请直接回复"<|endofconversation|>"。"""

st.set_page_config(
        "Character Chat",
        initial_sidebar_state="collapsed",
    )
st.write("""# 郭德纲来给您服务""")

#load plugins
_plugin_service = get_plugin_service()
function_name = []
function_meta = []
func = []
for plugin in _plugin_service._plugins:
    function_name.append(plugin['meta_info']['name'])
    function_meta.append(plugin['meta_info'])
    func.append(plugin['func'])
print("function_name: ", function_name)


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


def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-3.5-turbo', 'gpt-4-turbo', 'gpt-4'], index=1)
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
                'gpt-4-turbo',
                "gpt-4",
            }
        })
    config_list = [item.update({'presence_penalty': presence_penalty}) or item for item in config_list if
                   item['model'] == selected_model]
    llm_config = {
        "request_timeout": 600,
        "config_list": config_list
    }
    if function_meta:
        llm_config.update({'functions': function_meta})

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
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("<|endofconversation|>"),
        human_input_mode=human_input_mode,
        code_execution_config={'work_dir': 'coding'})
    #define all fucntion
    if function_name and func:
        assert len(function_name) == len(func)
        func_map = {}
        for i in range(len(func)):
            func_map.update({function_name[i]: func[i]})
        user_proxy.register_function(
            function_map= func_map
        )

    # streamlit ui start
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        if "function_call" in message:
            message['content'] = None
            with st.chat_message('assistant'):
                st.markdown(message["function_call"])
        elif "name" in message:
            with st.chat_message('user'):
                if message['name'].startswith('image_'):
                    st.image(message['content'], width=350)
                else:
                    st.markdown(message['content'])
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