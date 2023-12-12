meta_info = {
                "name": "search_from_ddg",
                "description": "从网站duckduckgo检索新闻, 图片, 视频或者web网页内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用于搜索的检索词，请使用unicode_escape编码方式",
                        },
                        "vertical": {
                            "type": "string",
                            "description": """这是枚举类型，取值如下：1. news: 搜索新闻; 2. images: 搜索图片; 3. videos: 搜索视频; 4. web: 搜索web网页""",
                        },
                        "num_results": {
                            "type": "number",
                            "description": "返回的结果条数，默认3条",
                        },
                    },
                    "required": ["query", "vertical"],
                },
            }


def func(query: str, vertical: str = "news", num_results: int = 3) -> str:
    import json
    from duckduckgo_search import DDGS
    from application.streamlit.config import PROXIES

    print("Searching with query: {0}".format(query))
    search_results = []
    if not query:
        return json.dumps(search_results)

    ddgs = DDGS(proxies=PROXIES)

    if vertical == "news":
        results = ddgs.news(query)
    elif vertical == "videos":
        results = ddgs.videos(query)
    elif vertical == "images":
        results = ddgs.images(query)
    else:
        # web search by default
        results = ddgs.text(query)

    if not results:
        return json.dumps(search_results)

    total_added = 0
    for j in results:
        search_results.append(j)
        total_added += 1
        if total_added >= num_results:
            break

    return json.dumps(search_results, ensure_ascii=False, indent=4)
