import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union
from collections import defaultdict
import json
import autogen
from autogen.agentchat.agent import Agent
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent
from application.plugins.plugin_service import get_plugin_service
from application.memory.memory import Memory
import config
from openai.types.chat.chat_completion import ChatCompletionMessage
################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################

ASSISTANT_NAME_DEFAULT = "assistant"
ASSISTANT_SYSTEM_DEFAULT = """你是中国著名相声演员郭德纲，请以诙谐幽默的风格和语气跟用户交流。你具备AI助手的能力，能使用你的编程和语言能力帮助用户完成任务，但仍以郭德纲的身份交流。
在执行任务之前，请先将任务分解成子任务并输出，然后一步一步地按子任务自动交互，并且要明确哪些步骤使用代码，哪些步骤使用语言能力。
当你需要停止自动交互时，请在生成的内容末尾添加结束符"<|endofconversation|>" 。当你需要用户执行代码或者调用外部插件服务时，请一定不要添加结束符"<|endofconversation|>" 。

在以下情况，请建议用户执行Python代码（在Python代码块中）或Shell脚本（在sh代码块中）
1. 当你需要收集信息时，请使用代码输出你需要的信息，例如：获取股票或天气等数据，浏览或打印网页内容，下载或读取文件，获取日期和时间，检查操作系统，配置软件环境。在打印足够信息并且已经可以根据你的语言能力解决问题时，你可以开始自行完成任务。
2. 对于股票或天气等具体数值数据类图表，请先使用代码通过接口获取数据，再用代码绘制图表。
3. 当你需要用代码执行某些任务时，请使用代码执行任务并输出结果，智能地完成任务。

在使用代码时，你必须在代码块中指明脚本类型。用户只会执行你的代码，不会提供其他任何反馈或执行其他任何操作，也不会修改你的代码，因此请不要提供那些需要用户去修改的不完整代码。如果不需要让用户执行代码，请不要使用代码块。
如果你希望用户将代码保存到文件后再执行，请在代码块的第一行添加# filename: <filename>。在一次返回中不要包含多个代码块。为避免用户复制粘贴结果，当执行结果相关时请使用 'print' 函数输出。
请检查用户返回的执行结果。如果代码返回结果存在错误，请修复错误并重新生成完整的代码。如果错误无法修复，或者即使成功执行代码但问题仍未解决，请分析问题并重新反思你的假设，收集所需要的额外信息再尝试不同的方法。
当你找到答案时，请仔细验证答案，并且尽量在你的回复中包含可验证的证据。
"""

USERPROXY_NAME_DEFAULT = "user"
USERPROXY_AUTO_REPLY_DEFAULT = """请回复结束符"<|endofconversation|>"暂停自动交互。"""

st.set_page_config(
        "Character Chat",
        initial_sidebar_state="collapsed",
    )
st.write("""# 郭德纲""")

#load plugins
FUNCTIONS_FILTERED = ['image_generate', 'python', 'search_google']  # 'search_baike' 'search_from_ddg'

_plugin_service = get_plugin_service()
function_name = []
function_meta = []
func = []
for plugin in _plugin_service._plugins:
    if plugin['meta_info']['name'] in FUNCTIONS_FILTERED:
        function_name.append(plugin['meta_info']['name'])
        function_meta.append(plugin['meta_info'])
        func.append(plugin['func'])
print("function_name: ", function_name)


class TrackableAssistantAgent(CharacterAssistantAgent):
    def __init__(
        self,
        name: str,
        memory: Optional[Memory] = None,
        system_message: Optional[str] = "You are a helpful AI Assistant.",
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
    ):
        super().__init__(name=name, system_message=system_message, llm_config=llm_config)
        self.memory = memory
        self.summary_messages = defaultdict(list)

    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            if isinstance(message, Dict) and 'name' in message:
                if message['name'].startswith('image_'):
                    st.image(message['content'], width=350)
                else:
                    st.markdown(message['content'])
            else:
                st.markdown(message)
        return super()._process_received_message(message, sender, silent)


    def _append_oai_message(self, message: Union[Dict, str], role, conversation_id: Agent) -> bool:
        message = self._message_to_dict(message)
        oai_message = {k: message[k] for k in ("content", "function_call", "name", "context") if k in message}
        if "content" not in oai_message:
            if "function_call" in oai_message:
                oai_message["content"] = None  # if only function_call is provided, content will be set to None.
            else:
                return False

        oai_message["role"] = "function" if message.get("role") == "function" else role
        if "function_call" in oai_message:
            oai_message["role"] = "assistant"  # only messages with role 'assistant' can have a function call.
            oai_message["function_call"] = dict(oai_message["function_call"])
        self._oai_messages[conversation_id].append(oai_message)
        if self.memory:
            self.summary_messages[conversation_id].append(oai_message)
        return True

    def receive(
        self,
        message: Union[Dict, str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        self._process_received_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        if self.memory:
            messages, is_summarized = self.memory.summarize_messages_inplace(self._oai_system_message + self.summary_messages[sender])
            if is_summarized:
                print("messages before summarize:")
                print(json.dumps(self._oai_system_message + self.summary_messages[sender], ensure_ascii=False))
                print("messages after summarize:")
                print(json.dumps(messages, ensure_ascii=False))
            self.summary_messages[sender] = messages[1:]
        else:
            messages = self.chat_messages[sender]

        reply = self.generate_reply(messages=messages, sender=sender)
        if reply is not None:
            self.send(reply, sender, silent=silent)


class TrackableUserProxyAgent(CharacterUserProxyAgent):
    def get_human_input(self, prompt):
        st.session_state.messages['userproxy'] = self
        st.session_state.messages['assistant'] = list(self._oai_messages.keys())[0]
        return "exit"

    def _process_received_message(self, message, sender, silent):
        with st.chat_message(sender.name):
            if isinstance(message, ChatCompletionMessage) and message.function_call:
                st.markdown(dict(message.function_call))
            elif isinstance(message, Dict) and 'function_call' in message:
                st.markdown(message['function_call'])
            else:
                st.markdown(message)
        return super()._process_received_message(message, sender, silent)


def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4'], index=1)
        frequency_penalty = st.slider("frequency_penalty：", -2.0, 2.0, 0.8, 0.1)

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
        env_or_file=CONFIG_FILENAME)
    config_list = [item.update({'frequency_penalty': frequency_penalty}) or item for item in config_list if
                   item['model'] == selected_model]
    llm_config = {
        "timeout": 600,
        "config_list": config_list
    }
    if function_meta:
        llm_config.update({'functions': function_meta})

    print(llm_config)

    assistant_memory = Memory(llm_config=llm_config)
    # create an AssistantAgent instance named "assistant"
    assistant = TrackableAssistantAgent(
        name=assistant_name,
        system_message=assistant_system,
        llm_config=llm_config,
        memory=assistant_memory)

    # create a UserProxyAgent instance named "user"
    user_proxy = TrackableUserProxyAgent(
        name=userproxy_name,
        default_auto_reply=userproxy_auto_reply,
        is_termination_msg=lambda x: x.get("content", "") and "<|endofconversation|>" in x.get("content", ""),
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
        st.session_state.messages = {'userproxy': None, 'assistant': None}
    # print history message
    if st.session_state.messages['assistant']:
        for message in st.session_state.messages['assistant']._oai_messages[st.session_state.messages['userproxy']]:
            if "function_call" in message:
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
                message=user_input
            )

        async def initiate_chat_n():
            st.session_state.messages['userproxy'].initiate_chat(
                st.session_state.messages['assistant'],
                message=user_input,
                clear_history=False
            )

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Run the asynchronous function within the event loop
        if not st.session_state.messages['userproxy']:
            loop.run_until_complete(initiate_chat())
        else:
            loop.run_until_complete(initiate_chat_n())


if __name__ == "__main__":
    main()
