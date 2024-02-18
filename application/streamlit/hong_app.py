import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, Set
from application.plugins.plugin_service import get_plugin_service
from application.hong.config import (config_list_from_json, Scene, get_wenxin_access_token)
import config
import openai, requests
import json
import dashscope
from http import HTTPStatus

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME

# qwen config
dashscope.api_key = "YOUR_DASHSCOPE_API_KEY"

#wenxin config
WENXIN_API_KEY = "YOUR_WENXIN_API_KEY"
WENXIN_SECRET_KEY = "YOUR_WENXIN_SECRET_KEY"
################################################################################################
PROMPT_TEMPLATE = """你是{identity}，现在你因为一件事情和你的{other_party}产生了矛盾，而你的{other_party}正在请求你的原谅。你要根据你的{other_party}说的话回话并选择原谅值，原谅值范围从-30到30，为正值则代表你心情有所好转，值越大则好转越多，为负值则代表你心情变差了，值越小则越差。

事件：
{event}

历史对话：
{history_conv}

"""
REPLY_FORMAT = """你的回答格式应该如下json格式：
{
"reply": "你回话的内容，要求尽量简短",
"forgiveness_value": "你给出的原谅值",
"expression": "你回话时的表情(没有表情则填写空字符串)，例如：思考、愤怒、开心、冷静等",
"action": "你回话时的动作(没有动作则填写空字符串)，例如：点头、摇头、皱眉、微笑等"
}"""

st.set_page_config(
    "Chat config",
    # initial_sidebar_state="collapsed",
)
st.write("""# 哄哄模拟器""")


def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4', 'qwen-max', 'wenxin-4.0'],
                                      index=1)

        dialogue_mode = st.selectbox("选择一个场景：",
                                     Scene.keys(),
                                     index=0,
                                     key="dialogue_mode",
                                     )
        if "previous_option" not in st.session_state:
            st.session_state.previous_option = dialogue_mode
        if "forgiveness_value" not in st.session_state:
            st.session_state.forgiveness_value = Scene[dialogue_mode]["init_mood_value"]
        if "allow_chatting" not in st.session_state:
            st.session_state.allow_chatting = True
        with st.expander("Scene Settings", True):
            st.markdown("<span style='color:red;'>场景： \n</span>" + Scene[dialogue_mode]["scenario_overview"],
                        unsafe_allow_html=True)
            st.markdown(
                "<span style='color:red;'>初始原谅值： \n</span>" + str(Scene[dialogue_mode]["init_mood_value"]) + "/100",
                unsafe_allow_html=True)
            st.markdown("<span style='color:red;'>允许对话轮次： \n</span>" + "10", unsafe_allow_html=True)

    # update llm_config
    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    if selected_model not in ['qwen-max', 'wenxin-4.0']:
        client = openai.AzureOpenAI(
            api_key=llm_config.get("api_key"),
            azure_endpoint=llm_config.get("base_url"),
            api_version=llm_config.get("api_version")
        )

    def llm_request(messages: List) -> str:
        print(messages)
        if selected_model not in ['qwen-max', 'wenxin-4.0']:
            content = client.chat.completions.create(
                model=llm_config.get("model"),
                temperature=1.0,
                messages=messages
            ).choices[0].message.content
        elif selected_model == 'qwen-max':
            completion = dashscope.Generation.call(
                dashscope.Generation.Models.qwen_max,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
            )
            content = completion.output.choices[0].message.content if completion.status_code == HTTPStatus.OK else ""
        elif selected_model == 'wenxin-4.0':
            url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token=" + get_wenxin_access_token(WENXIN_API_KEY, WENXIN_SECRET_KEY)
            payload = json.dumps({
                "messages": messages
            })
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            content = json.loads(response.text)['result']
        return content

    format_params = {
        'identity': Scene[dialogue_mode]['identity'],
        'other_party': Scene[dialogue_mode]['other_party'],
        'event': Scene[dialogue_mode]['event']
    }

    # streamlit ui start
    if "messages" not in st.session_state:
        st.session_state.messages = []
        if Scene[dialogue_mode]["init_conv"]:
            st.session_state.messages.append({'role': 'assistant', 'content': Scene[dialogue_mode]["init_conv"]})

    if st.session_state.previous_option != dialogue_mode:
        st.session_state.messages = [{'role': 'assistant', 'content': Scene[dialogue_mode]["init_conv"]}]
        st.session_state.forgiveness_value = Scene[dialogue_mode]["init_mood_value"]
        st.session_state.allow_chatting = True
    st.session_state.previous_option = dialogue_mode

    if st.session_state.forgiveness_value < 0 or st.session_state.forgiveness_value >= 100 or len(
            st.session_state.messages) // 2 == 10:
        st.session_state.allow_chatting = False
        if st.session_state.forgiveness_value >= 100:
            button_clicked = st.button("恭喜你哄哄成功！！！  点击再玩一次", type="primary")
        else:
            button_clicked = st.button("很遗憾哄哄失败，点击再玩一次", type="primary")
        if button_clicked:
            st.session_state.messages = [{'role': 'assistant', 'content': Scene[dialogue_mode]["init_conv"]}]
            st.session_state.forgiveness_value = Scene[dialogue_mode]["init_mood_value"]
            st.session_state.allow_chatting = True

    history_conv = []
    for message in st.session_state.messages:
        if message['role'] == 'user':
            history_conv.append(f"你{Scene[dialogue_mode]['other_party']}：{message['content']}")
            with st.chat_message('user'):
                st.markdown(message['content'])
        elif message['role'] == 'assistant':
            history_conv.append(f"你：{message['content']}")
            with st.chat_message('assistant'):
                if "forgiveness_value" not in message:
                    st.markdown(message['content'])
                else:
                    color = f"<span style='color:green;'>原谅值：+{message['forgiveness_value']}</span>" if int(message[
                                                                                                                'forgiveness_value']) > 0 else f"<span style='color:red;'>原谅值：{message['forgiveness_value']}</span>"
                    st.markdown(message['content'] + "&nbsp;" * 10 + color, unsafe_allow_html=True)

    if st.session_state.messages and st.session_state.allow_chatting:
        if user_input := st.chat_input("Type something...", key="prompt"):
            # Define an asynchronous function
            st.session_state.messages.append({'role': 'user', 'content': user_input})
            history_conv.append(f"你{Scene[dialogue_mode]['other_party']}：{user_input}")
            format_params['history_conv'] = "\n".join(history_conv)

            model_role = 'system' if selected_model not in ['qwen-max', 'wenxin-4.0'] else 'user'
            model_message = [{'role': model_role, 'content': PROMPT_TEMPLATE.format(**format_params) + REPLY_FORMAT}]
            with st.chat_message('user'):
                st.markdown(user_input)

            response_llm = llm_request(model_message)
            for _ in range(5):
                try:
                    start_idx = response_llm.index('{')
                    end_idx = response_llm.index('}')
                    response = json.loads(response_llm[start_idx:end_idx + 1])
                    reply = ""
                    reply += f"({response['expression']})" if response['expression'] else ""
                    reply += f"({response['action']})" if response['action'] else ""
                    reply += response['reply']

                    with st.chat_message('assistant'):
                        color = f"<span style='color:green;'>原谅值：+{response['forgiveness_value']}</span>" if int(
                            response[
                                'forgiveness_value']) > 0 else f"<span style='color:red;'>原谅值：{response['forgiveness_value']}</span>"
                        st.markdown(reply + "&nbsp;" * 10 + color, unsafe_allow_html=True)
                    st.session_state.messages.append(
                        {'role': 'assistant', 'content': reply, 'forgiveness_value': response['forgiveness_value']})
                    print(st.session_state.messages)

                    st.session_state.forgiveness_value += int(response['forgiveness_value'])
                    with st.sidebar:
                        st.markdown("<span style='color:red;'>当前原谅值： \n</span>" + str(
                            st.session_state.forgiveness_value) + "/100", unsafe_allow_html=True)
                        st.progress(len(st.session_state.messages) // 2 * 10,
                                    text=f"对话轮次：{len(st.session_state.messages) // 2}/10")
                    break
                except:
                    print("解析失败，模型返回内容：\n" + response_llm)
                    st.toast("解析失败，正在重试······")


if __name__ == "__main__":
    main()
