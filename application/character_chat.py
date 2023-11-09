from autogen import config_list_from_json
from autogen.agentchat.contrib.character_assistant_agent import CharacterAssistantAgent
from autogen.agentchat.contrib.character_user_proxy_agent import CharacterUserProxyAgent

if __name__ == "__main__":
    config_list = config_list_from_json(
        env_or_file="OAI_CONFIG_LIST",
        filter_dict={
            "model": {
                #"gpt-3.5-turbo",
                "gpt-4",
            }
        })
    assistant = CharacterAssistantAgent("character_assistant", llm_config={"config_list": config_list})
    user_proxy = CharacterUserProxyAgent("user_proxy", code_execution_config={"work_dir": "coding"})
    user_proxy.initiate_chat(assistant, message="hi")

