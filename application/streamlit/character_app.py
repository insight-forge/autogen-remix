import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, Set
from application.plugins.plugin_service import get_plugin_service
from application.character.config import (execute_function, config_list_from_json, system_message_visualize, CHARACTER)
import config
import openai

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################
st.set_page_config(
    "Character Chat",
    # initial_sidebar_state="collapsed",
)
st.write("""# Character Chat""")

# load plugins
FUNCTIONS_FILTERED = ['image_generate', 'search_google']  # 'search_baike' 'search_from_ddg'

_plugin_service = get_plugin_service()
function_name, function_meta, func = [], [], []
for plugin in _plugin_service._plugins:
    meta_info = plugin['meta_info']
    if meta_info['name'] in FUNCTIONS_FILTERED:
        function_name.append(meta_info['name'])
        function_meta.append(meta_info)
        func.append(plugin['func'])

if function_name and func:
    func_map = dict(zip(function_name, func))


# print("function_name: ", function_name)

def main():
    with st.sidebar:
        st.header("OpenAI Configuration")
        selected_model = st.selectbox("Model", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4'], index=1)

        dialogue_mode = st.selectbox("Please select a character:",
                                     CHARACTER.keys(),
                                     index=0,
                                     key="dialogue_mode",
                                     )
        SYSTEM_PROMPT = ""
        with st.expander("Character Settings", True):
            character_identity = st.text_area('identity', value=CHARACTER[dialogue_mode].get("identity", ""),
                                              help="Can fill in name, gender, age, date of birth, occupation, place of residence, family composition, property, etc")
            character_interest = st.text_area('interest', value=CHARACTER[dialogue_mode].get("interest", ""),
                                              help="Can fill in likes and dislikes")
            character_viewpoint = st.text_area('viewpoint', value=CHARACTER[dialogue_mode].get("viewpoint", ""),
                                               help="Can fill in worldview, philosophy of life, and values")
            character_experience = st.text_area('experience', value=CHARACTER[dialogue_mode].get("experience", ""),
                                                help="Can fill in past and present experiences")
            character_achieve = st.text_area('achieve', value=CHARACTER[dialogue_mode].get("achieve", ""),
                                             help="Can fill in awards and honors")
            character_personality = st.text_area('personality', value=CHARACTER[dialogue_mode].get("personality", ""),
                                                 help="Can fill in character personalities, such as gentle, indifferent, etc")
            character_socialize = st.text_area('socialize', value=CHARACTER[dialogue_mode].get("socialize", ""),
                                               help="Can fill in the description of the relationship with others")
            character_speciality = st.text_area('speciality', value=CHARACTER[dialogue_mode].get("speciality", ""),
                                                help="Can fill in skills, specialties, etc.")
            character_language_features = st.text_area('Language Features',
                                                       value=CHARACTER[dialogue_mode].get("language_features", ""),
                                                       help="Can fill in catchphrases, dialects, literary style features, favorite words and phrases, etc")

        system_list = ["Generate a character prompt, starting with 'you are', with the following known information:"]
        if character_identity:
            system_list.append(f"Identity: {character_identity}")
        if character_interest:
            system_list.append(f"Interest: {character_interest}")
        if character_viewpoint:
            system_list.append(f"Viewpoint: {character_viewpoint}")
        if character_experience:
            system_list.append(f"Experience: {character_experience}")
        if character_achieve:
            system_list.append(f"Achieve: {character_achieve}")
        if character_personality:
            system_list.append(f"Personality: {character_personality}")
        if character_socialize:
            system_list.append(f"Socialize: {character_socialize}")
        if character_speciality:
            system_list.append(f"Speciality: {character_speciality}")
        if character_language_features:
            system_list.append(f"Language features: {character_language_features}")

        if len(system_list) > 1:
            SYSTEM_PROMPT = "\n".join(system_list)
            print(SYSTEM_PROMPT)

    # update llm_config
    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    if function_meta:
        llm_config.update({'functions': function_meta})

    # print(llm_config)

    def openai_request(messages: List) -> Dict:
        completion = openai.ChatCompletion.create(
            deployment_id=llm_config['model'],
            api_key=llm_config['api_key'],
            api_version=llm_config['api_version'],
            api_base=llm_config['base_url'],
            api_type=llm_config['api_type'],
            functions=llm_config['functions'],
            messages=messages
        )
        return completion["choices"][0]['message']

    # streamlit ui start
    if "side_markdown" not in st.session_state:
        st.session_state.side_markdown = ""
    if st.session_state.side_markdown:
        with st.sidebar:
            st.markdown(st.session_state.side_markdown, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    # print history message
    if st.session_state.messages:
        for message in st.session_state.messages:
            if "name" in message:
                with st.chat_message('function', avatar="🤖"):
                    if message['name'].startswith('image_'):
                        st.image(message['content'], width=350)
                    else:
                        st.markdown(message['content'])
            elif message["role"] == 'user':
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            elif message["role"] == 'assistant':
                with st.chat_message(message["role"]):
                    if "function_call" in message:
                        st.markdown(message["function_call"])
                    else:
                        st.markdown(message["content"])
    else:
        system = ""
        if st.button("Generate characters through LLM") and SYSTEM_PROMPT:
            if SYSTEM_PROMPT != CHARACTER[dialogue_mode]["default_system_prompt"]:
                system = openai_request([{'role': 'user', 'content': SYSTEM_PROMPT}])['content']
            else:
                system = CHARACTER[dialogue_mode]["default_system_message"]
            system_message_visualize(system, st)
        elif st.button("Generate characters through concatenation") and SYSTEM_PROMPT:
            system = "Your character information is as follows:\n" + SYSTEM_PROMPT.replace(
                "Generate a character prompt, starting with 'you are', with the following known information:\n", "")
            system_message_visualize(system, st)

    if st.session_state.messages:
        if user_input := st.chat_input("Type something...", key="prompt"):
            # Define an asynchronous function
            st.session_state.messages.append({'role': 'user', 'content': user_input})
            with st.chat_message('user'):
                st.markdown(user_input)

            async def initiate_chat():
                message = openai_request(st.session_state.messages)
                content = message.get("function_call", message.get("content"))
                with st.chat_message('assistant'):
                    st.markdown(content)
                if "function_call" not in message:
                    st.session_state.messages.append({'role': 'assistant', 'content': content})
                else:
                    st.session_state.messages.append({'role': 'assistant', 'content': None, 'function_call': content})

                if "function_call" in message:
                    res = execute_function(message['function_call'], func_map)
                    st.session_state.messages.append(res)
                    with st.chat_message('function', avatar="🤖"):
                        if res['name'].startswith('image_'):
                            st.image(res['content'], width=350)
                        else:
                            st.markdown(res['content'])
                    print(st.session_state.messages)
                    message_sec = openai_request(st.session_state.messages)
                    content_sec = message_sec.get("function_call", message_sec.get("content"))

                    st.session_state.messages.append({'role': 'assistant', 'content': content_sec})
                    with st.chat_message('assistant'):
                        st.markdown(content_sec)
                print(st.session_state.messages)
                return

                # Create an event loop

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Run the asynchronous function within the event loop
            loop.run_until_complete(initiate_chat())


if __name__ == "__main__":
    main()
