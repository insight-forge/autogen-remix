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

# glm config
GLM_API_KEY = "YOUR_GLM_API_KEY"

#01万物
yi_api_key = ""
yi_headers = {
    'Authorization': f'Bearer {yi_api_key}',
    'Content-Type': 'application/json',
}
################################################################################################
st.set_page_config(
    "Chat config",
    # initial_sidebar_state="collapsed",
)

def messages_assemble(text, img_urls: List, model: str):
    messages = [{'role':'user', 'content': []}]
    if model in ['gpt-4-vision-preview', 'yi-vl-plus']:
        if text:
            messages[0]['content'].append({"type": "text", "text": text})
        if img_urls:
            for url in img_urls:
                messages[0]['content'].append({"type": "image_url", "image_url": {"url": url}})
    elif model == 'qwen-vl-max':
        if text:
            messages[0]['content'].append({"text": text})
        if img_urls:
            for url in img_urls:
                messages[0]['content'].append({"image": url})
    elif model == 'glm-4v':
        if text:
            messages[0]['content'].append({"type": "text", "text": text})
        if img_urls:
            for url in img_urls:
                messages[0]['content'].append({"type": "image_url", "image_url": url})
    return messages

def main():
    with st.sidebar:
        st.header("Configuration")
        selected_model = st.selectbox("Model", ['gpt-4-vision-preview', 'qwen-vl-max', 'glm-4v', 'yi-vl-plus'], index=0)
    # update llm_config
    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    if selected_model == 'gpt-4-vision-preview':
        client = openai.AzureOpenAI(
            api_key=llm_config.get("api_key"),
            azure_endpoint=llm_config.get("base_url"),
            api_version=llm_config.get("api_version")
        )
    elif selected_model == 'glm-4v':
        client = ZhipuAI(api_key=GLM_API_KEY)

    def llm_request(messages: List) -> str:
        print('****模型>>>>>>>>>>' + selected_model)
        print(messages)
        if selected_model == 'gpt-4-vision-preview':
            content = client.chat.completions.create(
                model=llm_config.get("model"),
                messages=messages,
                max_tokens=2000
            ).choices[0].message.content

        elif selected_model == 'qwen-vl-max':
            completion = dashscope.MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
            content = completion['output']['choices'][0]['message']['content'][0]['text']

        elif selected_model == 'glm-4v':
            content = client.chat.completions.create(
                model="glm-4v",
                messages=messages
            )

        return content

    # streamlit ui start
    image_urls = st.text_area('图片链接(不同图片换行分隔):')
    text = st.text_area('文本:')

    gen_button = st.button("点击生成", type="primary", help="点击对动态分类")

    if gen_button:
        if image_urls or text:
            mult_image_urls = image_urls.split('\n')
            processed_urls = [image_url for image_url in mult_image_urls if image_url]
            messages = messages_assemble(text, processed_urls)
            content = llm_request(messages)
            st.markdown(content)
if __name__ == "__main__":
    main()
