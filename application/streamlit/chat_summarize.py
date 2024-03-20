import streamlit as st
from typing import List
import config
from application.chat_summary.config import config_list_from_json, chat_hisory_process
import openai, requests
import json
from docx import Document
from http import HTTPStatus

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################
st.set_page_config(
    "Chat config",
    # initial_sidebar_state="collapsed",
)

PRE_PROMPT_CH = """有一份聊天记录，你需要用中文围绕每个所讨论的主题，对每个发言者的发言进行尽量详细的总结，要求{word_num}字以内。

注意：
1.聊天记录中带有<*image*>标识的内容，说明发言者发送了一张图片，紧随其后的内容是对图片的描述。
2.对于不同的主题用1,2,3等序号表示出来，要分不同的段落生成。

聊天记录如下：\n"""

PRE_PROMPT_EN = """There is a chat record where you need to summarize each speaker's speech in detail in Chinese around each discussed topic, with a requirement of no more than {wordnum} words.

Attention:
1. The content marked with <*image*> in the chat record indicates that the speaker sent an image, followed by a description of the image.
2. Use numbers such as 1, 2, and 3 to represent different topics, and generate them in different paragraphs.

The chat records are as follows:\n"""


def main():
    with st.sidebar:
        st.header("Configuration")
        selected_model = st.selectbox("Model", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4', ], index=1)
        language = st.selectbox("选择语种", ['简体中文', '英语'], index=0)
        word_num = st.text_input("限定总结字数", value="200")
    # update llm_config
    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    # if selected_model not in ['通义千问2.1']:
    client = openai.AzureOpenAI(
        api_key=llm_config.get("api_key"),
        azure_endpoint=llm_config.get("base_url"),
        api_version=llm_config.get("api_version")
    )

    def llm_request(messages: List) -> str:
        streaming_box = st.empty()
        full_response = []

        completion = client.chat.completions.create(
            model=llm_config.get("model"),
            temperature=1.0,
            messages=messages,
            stream=True
        )
        for chunk in completion:
            try:
                if chunk.choices[0].delta.content:
                    full_response.append(chunk.choices[0].delta.content)
                    result = ''.join(full_response)
                    print(result)
                    streaming_box.markdown(result)
            except:
                pass
        return "".join(full_response)

    # chat_history = st.text_area("聊天记录", value=DEFAULT_HISTORY, height=500, help="填入待总结的聊天记录")

    uploaded_file = st.file_uploader("请选择一个 DOCX 文件", type=['docx'])

    gen_button = st.button("点击生成", type="primary", help="点击生成聊天记录总结")

    if gen_button:

        chat_history = ""
        if uploaded_file is not None:
            # 显示文件信息
            st.toast("正在处理对话历史......")
            file_details = {"FileName": uploaded_file.name, "FileType": uploaded_file.type,
                            "FileSize": uploaded_file.size}
            print(file_details)
            chat_history = chat_hisory_process(Document(uploaded_file), st)

        if language == '简体中文':
            prompt = PRE_PROMPT_CH.format(**{'word_num': word_num}) + chat_history
        else:
            prompt = PRE_PROMPT_EN.format(**{'word_num': word_num}) + chat_history

        if chat_history:
            print(chat_history)
            st.toast("生成总结......")
            response = llm_request([{'role': 'user', 'content': prompt}])
        else:
            pass
        # st.markdown(response)


if __name__ == "__main__":
    main()
