meta_info = {
                "name": "search_google",
                "description": "search web results from google",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "query term for search internet. Please note that query only supports Chinese. if not, it MUST be translated to Chinese",
                        },
                        "vertical": {
                            "type": "string",
                            "description": "This value is an enumeration type, and its values are web: search web pages, image: search images, video: search videos, news: search news(if no result,please use web)",
                        },
                        "search_count": {
                            "type": "integer",
                            "description": "Number of search results",
                        },
                    },
                    "required": ["query","vertical"],
                },
            }

def func(**kwargs):
    import requests
    print("args: ", kwargs)
    data = kwargs
    url='http://10.139.17.136:8089/google_search'
    search_count=data.get("search_count",3)
    search_count=int(search_count)
    data["search_count"]=search_count
    response = requests.post(url, data=data)
    result=response.json()
    code=result.get('code',-1)
    if code==0:
        return result.get("search_results",[])

    return []