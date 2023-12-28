import openai
import tiktoken
import json


LLM_MAX_TOKENS = {
    "DEFAULT": 8192,
    ## OpenAI models: https://platform.openai.com/docs/models/overview
    # gpt-4
    "gpt-4-1106-preview": 128000,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-0613": 8192,
    "gpt-4-32k-0613": 32768,
    "gpt-4-0314": 8192,  # legacy
    "gpt-4-32k-0314": 32768,  # legacy
    # gpt-3.5
    "gpt-35-turbo-1106": 16385,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-3.5-turbo-0613": 4096,  # legacy
    "gpt-3.5-turbo-16k-0613": 16385,  # legacy
    "gpt-3.5-turbo-0301": 4096,  # legacy
}

WORD_LIMIT = 300
SUMMARY_PROMPT_SYSTEM = f"""
Your job is to summarize a history of previous messages in a conversation between an AI and a human user.
The conversation you are given is a from a fixed context window and may not be complete.
Messages sent by the AI are marked with the 'assistant' role.
The AI 'assistant' can also make calls to functions, whose outputs can be seen in messages with the 'function' role.
Messages the user sends are in the 'user' role.
Summarize what happened in the conversation from the perspective of the AI (use the second person).
Keep your summary less than {WORD_LIMIT} words, do NOT exceed this word limit.
Only output the summary, do NOT include anything else in your output.
"""

def count_tokens(s: str, model: str = "gpt-4") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(s))

def package_summarize_message(summary, summary_length, hidden_message_count, total_message_count, timestamp=None):
    context_message = (
        f"Note: prior messages ({hidden_message_count} of {total_message_count} total messages) have been hidden from view due to conversation memory constraints.\n"
        + f"The following is a summary of the previous {summary_length} messages:\n {summary}"
    )
    return context_message

def summarize_messages(
    context_window,
    message_sequence_to_summarize,
    llm_config,
):
    """Summarize a message sequence using GPT"""

    summary_prompt = SUMMARY_PROMPT_SYSTEM
    #summary_input = str(message_sequence_to_summarize)
    summary_input = json.dumps(message_sequence_to_summarize, ensure_ascii=False)

    message_sequence = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": summary_input},
    ]

    response = openai.ChatCompletion.create(
            deployment_id=llm_config['model'],
            api_key=llm_config['api_key'],
            api_version=llm_config['api_version'],
            api_base=llm_config['base_url'],
            api_type=llm_config['api_type'],
            messages=message_sequence
        )
    reply = response["choices"][0]["message"]["content"]
    return reply


class Memory(object):
    def __init__(
        self,
        llm_config=None,
        context_window=None,
        message_summary_warning_frac=0.7,
        message_summary_trunc_keep_n_last=3,
        message_summary_trunc_token_frac=0.75,
    ):
        self.llm_config = {"model": "gpt-4"}
        if isinstance(llm_config, dict):
            self.llm_config.update(llm_config)
        if context_window:
            self.context_window = context_window
        else:
            self.context_window = LLM_MAX_TOKENS[self.llm_config['model']] if self.llm_config['model'] in LLM_MAX_TOKENS else LLM_MAX_TOKENS["DEFAULT"]
        self.llm_config = llm_config
        self.message_summary_warning_frac = message_summary_warning_frac
        self.message_summary_trunc_keep_n_last = message_summary_trunc_keep_n_last
        self.message_summary_trunc_token_frac = message_summary_trunc_token_frac
        print(self.llm_config["model"] + " token limit: " + str(self.context_window))

    def summarize_messages_inplace(self, messages, cutoff=None, preserve_last_N_messages=True):
        assert messages[0]["role"] == "system", f"messages[0] should be system (instead got {messages[0]})"

        # Start at index 1 (past the system message),
        # and collect messages for summarization until we reach the desired truncation token fraction (eg 50%)
        # Do not allow truncation of the last N messages, since these are needed for in-context examples of function calling
        token_counts = [count_tokens(str(msg), self.llm_config['model']) for msg in messages]
        if sum(token_counts) < self.message_summary_warning_frac * self.context_window:
            print("***********no summary!, current token: " + str(sum(token_counts))  + " | summary token:" + str(self.message_summary_warning_frac * self.context_window) +  "************")
            return messages

        message_buffer_token_count = sum(token_counts[1:])  # no system message
        desired_token_count_to_summarize = int(message_buffer_token_count * self.message_summary_trunc_token_frac)
        candidate_messages_to_summarize = messages[1:]
        token_counts = token_counts[1:]
        if preserve_last_N_messages:
            candidate_messages_to_summarize = candidate_messages_to_summarize[:-self.message_summary_trunc_keep_n_last]
            token_counts = token_counts[:-self.message_summary_trunc_keep_n_last]

        # If at this point there's nothing to summarize, throw an error
        if len(candidate_messages_to_summarize) == 0:
            return messages

        # Walk down the message buffer (front-to-back) until we hit the target token count
        tokens_so_far = 0
        cutoff = 0
        for i, msg in enumerate(candidate_messages_to_summarize):
            cutoff = i
            tokens_so_far += token_counts[i]
            if tokens_so_far > desired_token_count_to_summarize:
                break
        # Account for system message
        cutoff += 1
        if cutoff == len(candidate_messages_to_summarize):
            cutoff += 1
        print(f"len(candidate_messages_to_summarize)={len(candidate_messages_to_summarize)} cutoff={cutoff}")

        message_sequence_to_summarize = messages[1:cutoff]  # do NOT get rid of the system message

        summary = summarize_messages(
            context_window=self.context_window,
            message_sequence_to_summarize=message_sequence_to_summarize,
            llm_config=self.llm_config,
        )
        # Metadata that's useful for the agent to see
        all_time_message_count = len(messages)
        remaining_message_count = len(messages[cutoff:])
        hidden_message_count = all_time_message_count - remaining_message_count
        summary_message_count = len(message_sequence_to_summarize)
        summary_message = package_summarize_message(summary, summary_message_count, hidden_message_count, all_time_message_count)
        packed_summary_message = {"role": "system", "content": summary_message}
        new_messages = [messages[0]] + [packed_summary_message] + messages[cutoff:]
        return new_messages

