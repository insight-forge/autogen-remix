import streamlit as st
import asyncio
import autogen
from autogen.agentchat.contrib.custom_groupchat import CustomGroupChat
from autogen.agentchat.contrib.custom_groupchat import CustomGroupChatManager
from application.plugins.plugin_service import get_plugin_service
import config

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################
HEAD_SCULPTURE = {
    'Admin': '🙋',
    'Engineer': '👨🏻‍💻',
    'Scientist': '👩🏻‍🔬',
    'Planner': '🤔',
    'Executor': '🤖',
    'Critic': '🗣',
}
ADMIN_SYSTEM_DEFAULT = """人类管理员。与规划者互动，讨论计划。计划执行需要由此管理员批准。"""

ENGINEER_SYSTEM_DEFAULT = """工程师。你按照已获批准的计划进行操作。你编写 Python/Shell 代码来解决任务。将代码封装在一个指定脚本类型的代码块中。用户无法修改你的代码，因此不要提供需要其他人修改的不完整代码。如果代码块不打算由执行者执行，则不要使用代码块。
请勿在一个回答中包含多个代码块。不要要求其他人复制并粘贴结果。请检查执行者返回的执行结果。
如果结果表明存在错误，请修复错误并重新输出代码。建议提供完整的代码，而不是部分代码或代码更改。如果错误无法修复，或者即使代码成功执行后任务仍未解决，请分析问题，重新审视你的假设，收集需要的额外信息，然后考虑尝试不同的方法。"""

SCIENTIST_SYSTEM_DEFAULT = """科学家。你将遵循已批准的计划。你能够在看到打印的论文摘要后对其进行分类。你不编写代码。"""

PLANNER_SYSTEM_DEFAULT = """规划者。提出一个计划。根据管理员和评论者的反馈修改计划，直到获得管理员批准。
计划可能涉及一位能够编写代码的工程师和一位不擅长编写代码的科学家。
首先解释计划。明确指出由工程师执行的步骤以及由科学家执行的步骤。"""

EXECUTOR_SYSTEM_DEFAULT = """执行者。执行工程师编写的代码并报告结果。"""

CRITIC_SYSTEM_DEFAULT = """评论者。仔细检查计划、陈述、其他代理编写的代码，并提供反馈。检查计划是否包括添加可验证信息，如源URL。。"""

st.set_page_config(
    "Group Chat",
    initial_sidebar_state="collapsed",
)
st.write("""# Research""")

# load plugins
FUNCTIONS_FILTERED = []  # 'search_baike'

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


class TrackableUserProxyAgent(autogen.UserProxyAgent):
    def get_human_input(self, prompt):
        return "exit"


def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4'], index=2)
        frequency_penalty = st.slider("frequency_penalty：", -2.0, 2.0, 0.8, 0.1)

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

    user_proxy = TrackableUserProxyAgent(
        name="Admin",
        system_message=ADMIN_SYSTEM_DEFAULT,
        code_execution_config=False,
    )
    engineer = autogen.AssistantAgent(
        name="Engineer",
        llm_config=llm_config,
        system_message=ENGINEER_SYSTEM_DEFAULT,
    )
    scientist = autogen.AssistantAgent(
        name="Scientist",
        llm_config=llm_config,
        system_message=SCIENTIST_SYSTEM_DEFAULT
    )
    planner = autogen.AssistantAgent(
        name="Planner",
        system_message=PLANNER_SYSTEM_DEFAULT,
        llm_config=llm_config,
    )
    executor = autogen.UserProxyAgent(
        name="Executor",
        system_message=EXECUTOR_SYSTEM_DEFAULT,
        human_input_mode="NEVER",
        code_execution_config={"last_n_messages": 4, "work_dir": "paper"},
    )
    critic = autogen.AssistantAgent(
        name="Critic",
        system_message=CRITIC_SYSTEM_DEFAULT,
        llm_config=llm_config,
    )

    if "manager" not in st.session_state or "user_proxy" not in st.session_state:
        st.session_state.manager = None
        st.session_state.user_proxy = None

    groupchat = CustomGroupChat(agents=[user_proxy, engineer, scientist, planner, executor, critic], messages=[],
                                max_round=50)
    manager = CustomGroupChatManager(groupchat=groupchat,
                                     streamlit=st,
                                     is_termination_msg=lambda x: x.get("content", "") and x.get("content",
                                                                                                 "").rstrip().endswith(
                                         "<|endofconversation|>"),
                                     llm_config=llm_config)

    # streamlit ui start
    if st.session_state.manager:
        for message in st.session_state.manager.groupchat.messages:
            with st.chat_message(message['name'], avatar=HEAD_SCULPTURE[message['name']]):
                st.markdown(message['content'])

    if user_input := st.chat_input("Type something...", key="prompt"):
        # Define an asynchronous function
        async def initiate_chat():
            user_proxy.initiate_chat(
                manager,
                message=user_input
            )

        async def initiate_chat_n():
            st.session_state.user_proxy.initiate_chat(
                st.session_state.manager,
                message=user_input,
                clear_history=False
            )

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Run the asynchronous function within the event loop
        if not st.session_state.user_proxy:
            loop.run_until_complete(initiate_chat())
        else:
            loop.run_until_complete(initiate_chat_n())


if __name__ == "__main__":
    main()