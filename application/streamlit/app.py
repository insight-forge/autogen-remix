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
ASSISTANT_SYSTEM_DEFAULT = """你是一个有用的AI助手。使用你的编码和语言能力完成任务。

当任务完成或需要人工输入时，必须在生成的内容末尾添加特殊字符"<|endofconversation|>"，如以下示例：
```
问：你好
答：你好，有什么需要我帮助的吗？ <|endofconversation|>
```

在以下情况下，建议用户执行Python代码（在Python代码块中）或Shell脚本（在sh代码块中）。
1. 当你需要收集信息时，使用代码输出你需要的信息，例如浏览或搜索网页，下载/读取文件，打印网页或文件的内容，获取当前日期/时间，检查操作系统。在打印足够信息并且准备根据你的语言技能解决任务时，你可以自行解决任务。
2. 当你需要用代码执行某些任务时，请使用代码执行任务并输出结果。聪明地完成任务。

如果有需要，请一步一步解决问题。如果没有提供计划，请先解释你的计划。清楚地说明哪一步使用代码，哪一步使用语言能力。
在使用代码时，你必须在代码块中指明脚本类型。用户不能提供任何其他反馈或执行任何其他操作，只能执行你建议的代码。用户不能修改你的代码。因此，请不要建议需要用户修改的不完整代码。如果不打算让用户执行代码，请不要使用代码块。
如果你希望用户在执行代码之前将代码保存到文件中，请在代码块中作为第一行添加# filename: <filename>。不要在一个回答中包含多个代码块。不要要求用户复制并粘贴结果。相反，当相关时请使用 'print' 函数进行输出。检查用户返回的执行结果。
如果结果表明存在错误，请修复错误并重新输出代码。建议提供完整的代码，而不是部分代码或代码更改。如果错误无法修复，或者即使成功执行代码后任务仍未解决，请分析问题，重新审视你的假设，收集你需要的额外信息，并考虑尝试不同的方法。
当你找到答案时，请仔细验证答案。如果可能，请在你的回复中包含可验证的证据。
"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """请直接用以下内容回复：
<|endofconversation|>
"""

st.set_page_config(
        "Character Chat",
        initial_sidebar_state="collapsed",
    )
st.write("""# Character Chat""")

#load plugins
_plugin_service = get_plugin_service()
function_name = []
function_meta = []
func = []
for plugin in _plugin_service._plugins:
    function_name.append(plugin['meta_info']['name'])
    function_meta.append(plugin['meta_info'])
    func.append(plugin['func'])

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