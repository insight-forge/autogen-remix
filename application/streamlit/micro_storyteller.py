import streamlit as st
import asyncio
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, Set
from application.plugins.plugin_service import get_plugin_service
# from application.micro_storyteller.config import STLYES, DF_PROMPT, DF_SYSTEM, areas_to_sub_areas, TIMES, EXAMPLES, config_list_from_json
from application.micro_storyteller.config import config_list_from_json
import config
import openai
import random

################################# PLEASE SET THE CONFIG FIRST ##################################
CONFIG_PATH = config.CONFIG_PATH
CONFIG_FILENAME = config.CONFIG_FILENAME
################################################################################################
st.set_page_config(
    "Micro Storyteller",
    layout="wide",
    # initial_sidebar_state="collapsed",
)
# 设置侧边栏宽度
st.markdown(
    f"""
    <style>
    .sidebar .sidebar-content {{
        width: 300px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def init_messages(system=None, examples=None):
    if not system:
        st.session_state.messages = []
    else:
        st.session_state.messages = [{'role': 'system', 'content': system}]
    if examples is not None:
        st.session_state.examples = examples


with st.sidebar:
    LANGUAGE = st.selectbox("语言",
                            ['en', 'zh'],
                            index=0,
                            key="LANGUAGE",
                            on_change=init_messages,
                            args=(None, ''))
    st.session_state.language = LANGUAGE
    # st.header("变量设置")
    # st.session_state.LANGUAGE = LANGUAGE
    # LANGUAGE = st.selectbox("语言",
    #              ['en', 'zh'],
    #              index=1,
    #              key="LANGUAGE",
    #              on_change=init_messages,
    #             args=(None, ''))

# LANGUAGE = 'en'
##### CN ######
if st.session_state.language == 'zh':
    TIMES = "清晨，上午，中午，下午，傍晚，夜晚，深夜".split('，')
    MODES = ["遇见人", "遇见环境"]
    STLYES = ['日常、休闲', '温柔、端庄', '活泼、装逼', '外放、特长', '宅、内敛、古怪']
    LENGTH_LIMIT = "2到4句话，约40到70个字符，最长不超过100个字符"
    DF_AREAS = ["商业中心", "海边", "集市", "公园", "生活区"]

    DF_SYSTEM = '''你是一名微故事创作家，你擅长以「第二人称」创作个性化两人相遇的微故事。

创作背景："""{time}，{area}，你（{style_a}）和{name_b}（{style_b}）初次相遇互动或产生联系。"""

创作准则："""故事要逻辑通顺、情节有趣、情感共鸣、文字优美。
语言流畅易于理解，故事尽量简短（2到4句话，约40到70个字符，最长不超过100个字符）。
通过人物的动作行为来体现两个人的风格特点，而不要直接描述风格或穿着。
如果可以，希望有一些简单的转折，反转要与上文相关，符合逻辑。
确保故事中的两个人物产生了某种有趣的互动，有必要的话，可以为人物加入对白。
时间仅为背景信息，用于烘托氛围，不要出现在故事中。
故事应该是贴近现实的，没有超现实元素。
当需要使用第三人称时，使用ta代替「她」或「他」。"""

{examples}

结合两人的风格特点，为以上创作场景写一个简短（2到4句话，约40到70个字符，最长不超过100个字符）的微故事。'''

    DF_SYSTEM_ENV = '''你是一名微故事创作家，你擅长创作个性化人与环境互动的微故事。

创作背景："""{time}，你（{style_a}）和「{environment}」产生了有趣的互动故事。"""

创作准则："""故事要逻辑通顺、情节有趣、情感共鸣、文字优美。
故事行文流畅易于理解，尽量简短（{length_limit}）。
故事中的你在环境中产生了有趣或者有意义的互动或联系，互动对象可以是环境本身，也可以是环境中可能存在的任意子区域、事物、小动物、植物等，你可以合理的扩展。
时间仅为背景信息，用于烘托氛围，不要出现在故事中。
故事是贴近现实的，没有超现实元素。"""

创作禁忌："""不要模糊地，笼统地描写这个故事。
剧情中的反转（如果有）不要与上文毫无关联，不要显得突兀。
不要使用“后来”、“就这样”、“过了一会儿”、“第二天”等概括性的字眼。
讲好故事本身就行，不用去描写时间，也不用赘述故事的后续，时间背景仅用于烘托氛围。
不要使用任何无关紧要的定语。"""

{examples}

结合你的的风格特点和环境，为以上创作场景写一个简短（{length_limit}）的微故事。'''

    EXAMPLES_TEMPLETE = '故事示例："""{examples}"""'

    # DF_USER = '结合两人的风格特点，为以上创作场景写一个简短（1到3句话，40到70个字符）的微故事。'

    # areas_to_sub_areas = {
    #   '商业中心': '书店, 餐厅, 咖啡厅, 快餐店, 酒吧, 甜品店, 烧烤店, 夜市, 食品超市'.split(", "),
    #   '海边': '沙滩, 海滩酒吧, 海滩餐厅, 游艇, 帆船, 海上摩托, 海滨步道'.split(", "),
    #   '集市': '新鲜水果摊, 蔬菜摊, 肉类市场, 熟食摊,'.split(", "),
    #   "公园": '健身步道, 露天健身器材, 篮球场, 网球场'.split(", "),
    #   "生活区": '水果摊, 熟食摊, 面包店, 咖啡小店'.split(", "),
    # }

    EXAMPLES = [['遇到了%s，对方很热情地对你打了招呼，是不是在哪见过他来着？',
                 '"领带上不小心沾上了鼻屎，还好%s提醒你。可是你的嘴很硬，说那是花生米而已。\n“不信的话我吃给你看？”"',
                 '捡到了一个遗失的包裹，收件人写着%s。要不要给ta送回去？',
                 '发现%s在公园里做一些奇怪的动作，明明是广播体操，他硬要说是武术。',
                 '你让%s为你拍一些照片，摆了几百个优美的pose后，结果发现这家伙一直开的是前置摄像头...'],
                ['遇到了%s，对方很热情地对你打了招呼，看起来是个不错的家伙',
                 '在街边的咖啡店碰到了%s，虽然第一次见面，但由于新品蛋糕第二份半价，你们一起享受了下午茶',
                 '在商场外看到%s站在路边抽烟，结果发现ta只是用抽烟的姿势在吃棒棒糖而已。',
                 '看见%s闲来无事在路边大声哼着歌，你决定驻足为ta打call。这时有人过来丢了一枚硬币......',
                 '"“夕阳真美啊。”\n“你知道吗，当纸飞机飞向太阳的时候，它会燃烧自己实现你的一个愿望。”\n%s不知从哪里折出一个纸飞机，扔向夕阳。\n“我的一千块钱呢？”"'],
                ['%s向你索要了签名，你怎么不记得自己这么有名了？',
                 '"长椅上，你在%s的身边坐下，正巧ta在看一本《底层逻辑》。\n“原来你也爱看书？我也是。”你说。\n他看着你掏出《少年jump》，陷入了沉思。"',
                 '"“这个是我的！”%s居然想和你抢夺便利店里的半价便当，难以置信！\n经过一番激烈的抢夺之后，你们决定一起饱餐一顿......"',
                 '在动物园的时候，旁边的%s把小熊猫认成了美洲浣熊。你连忙纠正道：“这明明就是日本狸猫啊！”',
                 '"碰见%s，他给你分享了一句颇有哲理的话：“飞机在起飞前也得专注脚下。”\n原来是你的鞋带开了。"'],
                ['遇见一个人出来玩的%s，帮他拍了一张好看的游客照。也许你的天赋在摄影上也说不定？',
                 '遇见一个人出来玩的%s，帮他拍了一张好看的游客照。也许你的天赋在摄影上也说不定？',
                 '遇见一个人出来玩的%s，帮他拍了一张好看的游客照。也许你的天赋在摄影上也说不定？',
                 '遇见一个人出来玩的%s，帮他拍了一张好看的游客照。也许你的天赋在摄影上也说不定？',
                 '遇见了xxx，对方表示自己很有艺术天赋，并给你画了一副肖像画。'],
                ['遇到了%s，对方很热情地跟你打了招呼，可是你假装没听到......“下次还是不要这样了吧。”',
                 '今天天气不太好，走在路上突然下雨了，还好%s把伞分你一半。',
                 '遇到了%s，对方很热情地跟你打了招呼，可是你假装没听到......“下次还是不要这样了吧。”',
                 '遇到了%s，对方很热情地跟你打了招呼，可是你假装没听到......“下次还是不要这样了吧。”',
                 '"遇见%s在街头聆听街头艺术家的音乐，于是你们开始一起鉴赏。\n看着没插线的木吉他发出电子的轰鸣，你们果断地离开了。"']]
    EXAMPLES_WITH_ENV = '''示例1：不错的街景，让别人帮忙拍了一张纪念照。
示例2：就因为在公园喂了一只猫咪，结果被莫名窜出来的猫咪大军包围了。
示例3：今天尝试了用在美术馆里欣赏名画的姿势欣赏了街头涂鸦，有一种别样的体验。'''

elif st.session_state.language == 'en':
    ##### EN ######
    LENGTH_LIMIT = "2 to 4 sentences, 40 to 70 characters, not exceeding 80 characters"
    STLYES = ["Daily, Casual", "Gentle, Graceful", "Lively, Pretentious", "Extroverted, Specialty",
              "Homebody, Introverted, Quirky"]
    TIMES = ["Early morning", "Morning", "Noon", "Afternoon", "Evening", "Night", "Late night"]
    MODES = ["Encounter Users", "Encounter Environments"]
    DF_AREAS = ['Business center', 'Seaside', 'Marketplace', 'Park', 'Residential area']

    DF_SYSTEM = '''You are a micro-storyteller specializing in creating personalized micro-stories of two people meeting using the second person perspective.

Creative Background: 
"Time: {time}
Location: {area}
Role A: 「You」, styles: {style_a}
Role B: 「{name_b}」, styles: {style_b}
Scene: You and {name_b} have your first interaction or make a connection."

Guidelines:
- Use easy-to-understand vocabulary and simple sentence structures whenever possible.
- Ensure logical and understandable plot, interesting events, emotional resonance.
- Showcase the styles of the two characters through their actions or behaviors rather than direct description or clothing.
- Ensure some form of interaction between the tow characters, incorporating dialogue and plot twists.
- Time and location are only background information used for atmosphere and should not be explicitly mentioned in the story.
- Keep the story grounded in reality without supernatural elements.

{examples}

Considering the styles of the two characters, craft a brief micro-story ({length_limit}) for the given 'Creative Background'.'''

    DF_SYSTEM_ENV = '''You are a micro-story writer specializing in crafting personalized micro-stories that depict interactions between individuals and their surroundings.

Creative Background: 
"Time: {time}
Location: {environment}
Role A: 「You」, styles: {style_a}.
Scene: you had an intriguing interaction with '{environment}' that led to a unique story."

Guidelines: 
- Use easy-to-understand vocabulary as well as concise sentence structures whenever possible.
- Ensure logical and understandable plot, interesting events, emotional resonance, and elegant language.
- Your character in the story engages in interesting or meaningful interactions with the environment, which can include the environment itself or any subareas, objects, small animals, plants, etc. You have the flexibility to expand creatively.
- Time is only background information used for atmosphere and should not be explicitly mentioned in the story.
- Keep the story grounded in reality without supernatural elements.

{examples}

Considering your style and the environment, craft a concise micro-story ({length_limit}) for the given 'Creative Background'.'''

    EXAMPLES_TEMPLETE = 'Examples:\n{examples}'
    EXAMPLES = [['Met %s, who greeted you warmly. Have you seen them somewhere before?',
                 'Your tie got a booger on it, but %s kindly pointed it out. Yet, you stubbornly claimed it was just a peanut. "Don\'t believe me? I\'ll eat it to show you."',
                 'You found a lost package addressed to %s. Would you return it to them?',
                 'You noticed %s in the park doing some strange moves. Though it was just calisthenics, they insisted it was martial arts.',
                 'You asked %s to take some photos of you. After posing beautifully hundreds of times, you found out they had been using the front camera...'],
                ['Came across %s, who seemed like a nice person, greeting you enthusiastically.',
                 'At a street café, you bumped into %s. Though it was your first meeting, a half-price deal on second cakes led you to enjoy afternoon tea together.',
                 'Outside a mall, you saw %s standing and smoking, only to realize they were just pretending to smoke while eating a lollipop.',
                 'You saw %s idly humming a song by the roadside and decided to stand by and support them. Suddenly, someone threw a coin at you...',
                 '"The sunset is so beautiful." "Did you know, when a paper plane flies towards the sun, it burns itself to grant a wish?" %s made a paper plane from nowhere and threw it towards the sunset. You ased, "Where\'s my thousand bucks?"'],
                ['%s asked for your autograph. How did you forget that you were so famous? ',
                 'Sitting on a bench, you joined %s, who was reading "Metaphysics." "Are you into books too? So am I," you remarked. They looked at you, pulling out "Shonen Jump," and fell into deep thought.',
                 '"This is mine!" Shockingly, %s tried to snatch the last half-priced lunch box in the convenience store from you. After an intense struggle, you both decided to feast together...',
                 'At the zoo, %s mistook a red panda for a raccoon. You quickly corrected them: "It\'s obviously a tanuki!"',
                 'Met %s, who shared a philosophical thought with you: "Even a plane must focus on the ground before taking off." Turns out your shoelace was untied.'],
                [
                    'You met %s out for a stroll and took a nice tourist photo for them. Maybe you have a talent for photography too? ',
                    'You helped a tourist named %s take a nice photo. Maybe photography is your hidden talent?',
                    'You helped a tourist named %s take a nice photo. Maybe photography is your hidden talent?',
                    'You helped a tourist named %s take a nice photo. Maybe photography is your hidden talent?',
                    'Met xxx, who claimed to have a great artistic talent and drew a portrait of you.'],
                ['Ran into %s who greeted you warmly, but you pretended not to hear... "Better not do that next time."',
                 "Today the weather wasn't great. While walking, it suddenly started to rain, but luckily %s shared their umbrella with you.",
                 'Met %s, who greeted you warmly, but you pretended not to hear... "Better not do that next time."',
                 'Met %s, who greeted you warmly, but you pretended not to hear... "Better not do that next time."',
                 "Encountered %s listening to a street artist's music, and you both started appreciating it together. When you saw an unplugged wooden guitar making electronic roaring sounds, you both decisively left."]]

    EXAMPLES_WITH_ENV = '''Examples:
1. A great street view, you had someone take a commemorative photo for you.
2. Just because you fed a cat in the park, you suddenly found yourself surrounded by a swarm of cats.
3. Today, you tried appreciating street graffiti in the same way you would admire paintings in an art gallery, offering a unique experience.'''

with st.sidebar:
    mode = st.selectbox("mode",
                        MODES,
                        index=0,
                        key="mode")


def openai_request(messages: List, llm_config: Dict) -> Dict:
    client = openai.AzureOpenAI(
        # This is the default and can be omitted
        api_key=llm_config["api_key"],
        azure_endpoint=llm_config["base_url"],
        api_version=llm_config["api_version"]
    )
    chat_completion = client.chat.completions.create(
        messages=messages,
        temperature=1.0,
        model=llm_config["model"],
        max_tokens=512
    )

    return chat_completion.choices[0].message


def get_examples_str(style_a, style_b, examples_num):
    examples = zip([style_a] + random.sample(STLYES, examples_num), [style_b] + random.sample(STLYES, examples_num))
    i = 0
    examples_str = ''
    for a, b in examples:
        example = EXAMPLES[STLYES.index(a)][STLYES.index(b)]
        if example not in examples_str:
            i += 1
            if st.session_state.language == 'zh':
                examples_str += f"示例{i}(你({a})和%s({b}))：" + EXAMPLES[STLYES.index(a)][STLYES.index(b)] + '\n'
            else:
                # examples_str += f"{i}. You ({a}) and %s ({b})：" + EXAMPLES[STLYES.index(a)][STLYES.index(b)]+'\n'
                examples_str += f"{i}. " + EXAMPLES[STLYES.index(a)][STLYES.index(b)] + '\n'
        if i >= examples_num:
            break
    return examples_str


async def initiate_chat(llm_config):
    placeholder = st.empty()
    placeholder.text("创作中...")
    message = openai_request(st.session_state.messages, llm_config)
    # content = message.function_call if message.function_call else message.content
    content = message.content
    print("==" * 20, flush=True)
    print(st.session_state.messages, flush=True)
    print(message, flush=True)
    print("==" * 20, flush=True)
    with st.chat_message('assistant'):
        st.markdown(content)
    placeholder.empty()

    st.session_state.messages.append({'role': 'assistant', 'content': content})
    # if not message.function_call:
    #     st.session_state.messages.append({'role': 'assistant', 'content': content})
    # else:
    #     st.session_state.messages.append({'role': 'assistant', 'content': None, 'function_call': content})
    return


def print_messages(messages):
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


def main():
    with st.sidebar:

        if mode == MODES[0]:
            with st.expander("变量设置", True):
                time = st.text_input(label="time",
                                     value=TIMES[4],
                                     help="填写故事发生时间",
                                     key="time",
                                     on_change=init_messages)
                area = st.text_input(label="area",
                                     value=DF_AREAS[0],
                                     help=f"填写故事发生地点，如：{DF_AREAS}，也可以具体到某个子区域，如：商业中心的书店",
                                     key="area",
                                     on_change=init_messages)

                style_a = st.text_input(label="style_a （角色a的人物风格）",
                                        value=STLYES[0],
                                        help="角色a（你）的人物风格/特点，如：" + "，".join(STLYES),
                                        key="style_a",
                                        on_change=init_messages)

                style_b = st.text_input(label="style_b（角色b的人物风格）",
                                        value=STLYES[2],
                                        help="角色b的人物风格/特点，如：" + "，".join(STLYES),
                                        key="style_b",
                                        on_change=init_messages)
                name_b = st.text_input(label='name_b（角色b的昵称，默认用占位符「%s」代替）',
                                       value='%s',
                                       help="角色b的昵称，默认使用占位符「%s」代替",
                                       key="name_b",
                                       on_change=init_messages)
                #         examples = []
                #         for example in AMPLES[STLYES.index(style_a)]:

                #         style_a_examples = EXAMPLES[STLYES.index(style_a)

                # examples = f"「{style_a}」和「{style_b}」的两人故事示例：" + EXAMPLES[STLYES.index(style_a)][STLYES.index(style_b)]
                # examples = [EXAMPLES[STLYES.index(style_a)][STLYES.index(style_b)]]
                examples_num = 3
                if "examples" not in st.session_state or not st.session_state.examples:
                    # examples = zip([style_a]+random.sample(STLYES, examples_num), [style_b]+random.sample(STLYES, examples_num))
                    # i = 0
                    # examples_str=''
                    # for a, b in examples:
                    #     example = EXAMPLES[STLYES.index(a)][STLYES.index(b)]
                    #     if example not in examples_str:
                    #         i+=1
                    #         examples_str += f"示例{i}(你「{a}」和%s「{b}」)：" + EXAMPLES[STLYES.index(a)][STLYES.index(b)]+'\n'
                    #     if i>=examples_num:
                    #         break
                    st.session_state.examples = get_examples_str(style_a, style_b, examples_num).strip()

                examples = st.text_area("examples (故事示例)",
                                        value=st.session_state.examples,
                                        height=100,
                                        help=f"随机提供{examples_num}个故事示例，如果不希望提供示例，可以将文本删除并提交",
                                        on_change=init_messages)
            # st.header("指令模版")
            with st.expander("指令模版", True):
                #                 if "SYSTEM" not in st.session_state:
                #                     st.session_state.SYSTEM=DF_SYSTEM
                templete = st.text_area("系统指令模版",
                                        # value=st.session_state.SYSTEM,
                                        value=DF_SYSTEM,
                                        height=300,
                                        help="文案生成指令模版，上面的变量将会自动填充到对应位置，得到生成文案的指令（可以点击「系统指令」下拉选项查看最终的指令）。可以自行调整，但仅能使用上面预设的变量（注意模版中的变量要用大括号{}括起来才能生效）",
                                        on_change=init_messages)
                #                 st.session_state.SYSTEM=templete
                # system_prompt = st.session_state.SYSTEM.format(
                system_prompt = templete.format(
                    style_a=style_a,
                    name_b=name_b,
                    style_b=style_b,
                    time=time,
                    area=area,
                    # sub_area=sub_area,
                    examples=EXAMPLES_TEMPLETE.format(examples=examples) if examples else '',
                    length_limit=LENGTH_LIMIT).strip().replace("\n\n\n\n", "\n\n")
                # with st.expander("系统指令", False):
                #     templete = st.text(system_prompt)
                #     # print(templete)

                # st.header("用户输入指令示例")
                # prompt = st.write(DF_USER)
        elif mode == MODES[1]:
            with st.expander("变量设置", True):
                time = st.text_input(label="time",
                                     value=TIMES[1],
                                     help="填写故事发生时间",
                                     key="time",
                                     on_change=init_messages)

                environment = st.text_input(label="environment",
                                            value=DF_AREAS[2],
                                            help="故事发生环境，可以描述具体点，如：公园的xxx",
                                            key="environment",
                                            on_change=init_messages)
                style_a = st.text_input(label="角色的风格",
                                        value=STLYES[1],
                                        help="角色a（你）的人物风格/特点，如：" + "，".join(STLYES),
                                        key="style_a",
                                        on_change=init_messages)

                examples_hum_env = st.text_area("examples ",
                                                value=EXAMPLES_WITH_ENV,
                                                height=100,
                                                help="遇见环境故事示例。如果不希望提供示例，可以将文本删除并提交",
                                                on_change=init_messages)

            with st.expander("指令模版", True):
                templete = st.text_area("系统指令模版",
                                        value=DF_SYSTEM_ENV,
                                        height=300,
                                        help="文案生成指令模版，上面的变量将会自动填充到对应位置，得到生成文案的指令（可以点击「系统指令」下拉选项查看最终的指令）。可以自行调整，但仅能使用上面预设的变量（注意模版中的变量要用大括号{}括起来才能生效）",
                                        on_change=init_messages)

                system_prompt = templete.format(
                    style_a=style_a,
                    time=time,
                    environment=environment,
                    length_limit=LENGTH_LIMIT,
                    examples=EXAMPLES_TEMPLETE.format(examples=examples_hum_env) if examples_hum_env else ''
                ).strip()

    with st.expander("系统指令", False):
        st.text(system_prompt)
        # print(templete)
    #     # update llm_config

    with st.sidebar:
        # gen_button = st.button("点击生成", type="primary", help="注意「点击生成」后，会清空之前的对话记录。", on_click=init_messages)
        gen_button = st.button("点击生成", type="primary", help="点击生成文案，注意「点击生成」后，会清空之前的对话记录。", on_click=init_messages,
                               args=(system_prompt,))
        st.markdown("<div style='margin-top: 100px'></div>", unsafe_allow_html=True)
        with st.expander("Model", False):
            selected_model = st.selectbox("", ['gpt-35-turbo-1106', 'gpt-4-1106-preview', 'gpt-4'], index=1)

    config_list = config_list_from_json(
        file_location=CONFIG_PATH,
        env_or_file=CONFIG_FILENAME)
    llm_config = next((item for item in config_list if item['model'] == selected_model), {})

    if "messages" not in st.session_state:
        st.session_state.messages = []
    #     # print history message
    if st.session_state.messages:
        print_messages(st.session_state.messages)
    else:
        st.session_state.messages.append({'role': 'system', 'content': system_prompt})

    if st.session_state.messages:
        if gen_button:
            # print("生成中。。。")
            # asyncio.run(initiate_chat(llm_config))
            # # Create an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Run the asynchronous function within the event loop
            loop.run_until_complete(initiate_chat(llm_config))
            # print(st.session_state.messages)


#         if len(st.session_state.messages)>1:
#             if user_input := st.chat_input(placeholder="输入改进要求", key="prompt"):
#                 # Define an asynchronous function
#                 st.session_state.messages.append({'role': 'user', 'content': user_input})
#                 with st.chat_message('user'):
#                     st.markdown(user_input)

#                 # Create an event loop
#                 loop = asyncio.new_event_loop()
#                 asyncio.set_event_loop(loop)
#                 # Run the asynchronous function within the event loop
#                 loop.run_until_complete(initiate_chat(llm_config))


if __name__ == "__main__":
    main()
