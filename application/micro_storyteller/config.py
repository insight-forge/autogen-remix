from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, Set
import os, json, logging, re
import streamlit
import openai
CHARACTER = {"Custom Character": {"default_system_prompt": ""}}

STLYES = ['日常、休闲', '温柔、端庄', '活泼、装逼', '外放、特长', '宅、内敛、古怪']

DF_PROMPT = '''你是一名微故事创作家，你擅长以「第二人称」创作具有深度的微故事，你正在进行微故事创作。

创作场景："""某个{time}, 你{role_a}（{style_a}）在{area}{sub_area}和某个的陌生人{role_b}（{style_b}）第一次相遇。"""

创作准则："""文字尽量简短：1到3句话，40至70字最优，最长不超过100个字
通过故事内容来体现两个人的风格特点，而不要直接描述风格。
语言需要简洁风趣，请模仿一些简短的冷笑话风格，或是模仿日本动漫的一些叙事方式。参考作品：《银魂》
有必要的话，可以为人物加入对白
确保故事中的两个人物产生了某种有趣的和谐的互动
如果可以，希望有一些简单的反转，但必须确保反转是和谐自然的。
时间仅为背景信息，用于烘托氛围，不要出现在故事中
故事应该是贴近现实的，没有超现实元素"""

创作禁忌："""不要讨论宗教、政治、性别、种族相关的问题
不要模糊地，笼统地描写这个故事。不要使用“后来”、“就这样”、“过了一会儿”、“第二天”等概括性的字眼
讲好故事本身就行，不用去描写时间和空间背景，也不用赘述故事的后续，时间背景仅用于烘托氛围
不要使用任何无关紧要的定语"""

创作示例："""{samples}"""

参考以上创作示例，结合两人的风格特点，为以上创作场景写一个非常简短（1到2句话或40到70个字符）的微故事。'''

DF_SYSTEM = '''你是一名微故事创作家，你擅长以「第二人称」创作具有深度的微故事。

创作背景："""某个{time}, 你{role_a}（{style_a}）在{area}{sub_area}和某个的陌生人{role_b}（{style_b}）第一次相遇。"""

创作准则："""文字尽量简短：1到3句话，40至70字最优，最长不超过100个字
通过故事内容来体现两个人的风格特点，而不要直接描述风格。
语言需要简洁风趣，请模仿一些简短的冷笑话风格，或是模仿日本动漫的一些叙事方式。参考作品：《银魂》
有必要的话，可以为人物加入对白
确保故事中的两个人物产生了某种有趣的和谐的互动
如果可以，希望有一些简单的反转，但必须确保反转是和谐自然的。
时间仅为背景信息，用于烘托氛围，不要出现在故事中
故事应该是贴近现实的，没有超现实元素"""

创作禁忌："""不要讨论宗教、政治、性别、种族相关的问题
不要模糊地，笼统地描写这个故事。不要使用“后来”、“就这样”、“过了一会儿”、“第二天”等概括性的字眼
讲好故事本身就行，不用去描写时间和空间背景，也不用赘述故事的后续，时间背景仅用于烘托氛围
不要使用任何无关紧要的定语"""

创作示例："""{samples}"""'''

areas_to_sub_areas = {
  '商业中心': '书店, 餐厅, 咖啡厅, 快餐店, 酒吧, 甜品店, 烧烤店, 夜市, 食品超市'.split(", "),
  '海边': '沙滩, 海滩酒吧, 海滩餐厅, 游艇, 帆船, 海上摩托, 海滨步道'.split(", "),
  '集市': '新鲜水果摊, 蔬菜摊, 肉类市场, 熟食摊,'.split(", "),
  "公园": '健身步道, 露天健身器材, 篮球场, 网球场'.split(", "),
  "生活区": '水果摊, 熟食摊, 面包店, 咖啡小店'.split(", "),
}
TIMES = "清晨，上午，中午，下午，傍晚，夜晚，深夜".split('，')

SAMPLES = [['遇到了%s，对方很热情地对你打了招呼，是不是在哪见过他来着？',
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


_basedir = os.path.dirname(os.path.abspath(__file__))
for dir in os.listdir(_basedir):
    if dir.startswith("Character_"):
        character = re.sub(r'^Character_|\.py$', '', dir)
        with open(os.path.join(_basedir, dir), mode="r", encoding="utf-8") as py_file:
            py_code = py_file.read()

        output = {}
        exec(py_code, {"__name__": "__main__"}, output)
        assert character in output
        CHARACTER[character.replace("_", " ")] = output[character]


def system_message_visualize(system: str, st: streamlit):
    side_markdown = "<span style='color:red;'>system message:  \n</span>" + system.replace("\n", "  \n")
    st.session_state.side_markdown = side_markdown
    with st.sidebar:
        st.markdown(side_markdown, unsafe_allow_html=True)
    st.session_state.messages.append({'role': 'system', 'content': system})


def config_list_from_json(
        env_or_file: str,
        file_location: Optional[str] = ""
) -> List[Dict]:
    json_str = os.environ.get(env_or_file)
    if json_str:
        config_list = json.loads(json_str)
    else:
        config_list_path = os.path.join(file_location, env_or_file)
        try:
            with open(config_list_path) as json_file:
                config_list = json.load(json_file)
        except FileNotFoundError:
            logging.warning(f"The specified config_list file '{config_list_path}' does not exist.")
            return []
    return config_list


def _format_json_str(jstr):
    result = []
    inside_quotes = False
    last_char = " "
    for char in jstr:
        if last_char != "\\" and char == '"':
            inside_quotes = not inside_quotes
        last_char = char
        if not inside_quotes and char == "\n":
            continue
        if inside_quotes and char in ("\n", "\t"):
            char = "\\" + char
        result.append(char)
    return "".join(result)


def execute_function(func_call, _function_map) -> Dict[str, str]:
    func_name = func_call.get("name", "")
    func = _function_map.get(func_name, None)

    is_exec_success = False
    if func is not None:
        # Extract arguments from a json-like string and put it into a dict.
        input_string = _format_json_str(func_call.get("arguments", "{}"))
        try:
            arguments = json.loads(input_string)
        except json.JSONDecodeError as e:
            arguments = None
            content = f"Error: {e}\n You argument should follow json format."

        # Try to execute the function
        if arguments is not None:
            try:
                content = func(**arguments)
                is_exec_success = True
            except Exception as e:
                content = f"Error: {e}"
    else:
        content = f"Error: Function {func_name} not found."

    return {
        "name": func_name,
        "role": "function",
        "content": str(content),
    }