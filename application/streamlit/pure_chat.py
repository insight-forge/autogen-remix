import streamlit as st
from typing import List
from application.hong.config import (config_list_from_json, Scene, get_wenxin_access_token)
import config
import openai, requests
import json
import dashscope
from http import HTTPStatus
from zhipuai import ZhipuAI

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME

# qwen config
dashscope.api_key = "YOUR_DASHSCOPE_API_KEY"

# wenxin config
WENXIN_API_KEY = "YOUR_WENXIN_API_KEY"
WENXIN_SECRET_KEY = "YOUR_WENXIN_SECRET_KEY"

# glm config
GLM_API_KEY = "YOUR_GLM_API_KEY"
################################################################################################
st.set_page_config(
    "Chat config",
    # initial_sidebar_state="collapsed",
)


def main():
    with st.sidebar:
        st.header("Configuration")
        selected_model = st.selectbox("Model",
                                      ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4', '通义千问2.1', '文心一言4.0',
                                       'glm-4'], index=1)
    # update llm_config
    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    if selected_model not in ['通义千问2.1', '文心一言4.0', 'glm-4']:
        client = openai.AzureOpenAI(
            api_key=llm_config.get("api_key"),
            azure_endpoint=llm_config.get("base_url"),
            api_version=llm_config.get("api_version")
        )

    def llm_request(messages: List) -> str:
        print('****模型>>>>>>>>>>' + selected_model)
        print(messages)
        if selected_model not in ['通义千问2.1', '文心一言4.0', 'glm-4']:
            content = client.chat.completions.create(
                model=llm_config.get("model"),
                temperature=1.0,
                messages=messages
            ).choices[0].message.content

        elif selected_model == '通义千问2.1':
            completion = dashscope.Generation.call(
                dashscope.Generation.Models.qwen_max,
                messages=messages,
                result_format='message',  # set the result to be "message" format.
            )
            content = completion.output.choices[0].message.content if completion.status_code == HTTPStatus.OK else ""

        elif selected_model == '文心一言4.0':
            url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token=" + get_wenxin_access_token(
                WENXIN_API_KEY, WENXIN_SECRET_KEY)
            payload = json.dumps({
                "messages": messages
            })
            headers = {
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            content = json.loads(response.text)['result']

        elif selected_model == 'glm-4':
            client_glm = ZhipuAI(api_key=GLM_API_KEY)
            content = client_glm.chat.completions.create(
                model="glm-4",
                messages=messages
            ).choices[0].message.content
        return content

    # streamlit ui start
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        if message['role'] == 'user':
            with st.chat_message('user'):
                st.markdown(message['content'])
        elif message['role'] == 'assistant':
            with st.chat_message('assistant'):
                st.markdown(message['content'])

    if user_input := st.chat_input("Type something...", key="prompt"):
        st.session_state.messages.append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.markdown(user_input)

        response_llm = llm_request(st.session_state.messages)
        st.session_state.messages.append({'role': 'assistant', 'content': response_llm})
        with st.chat_message('assistant'):
            st.markdown(response_llm)


if __name__ == "__main__":
    main()
