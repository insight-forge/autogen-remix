meta_info = {
                "name": "search_baike",
                "description": "If the user is asking some factual questions, please use this method to query the results",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kws": {
                            "type": "string",
                            "description": "key words for factual questions",
                        }
                    },
                    "required": ["kws"],
                },
            }

def func(**kwargs):
    import requests
    data = kwargs
    kws=data.get('kws','')
    url=f"https://baike.baidu.com/api/openapi/BaikeLemmaCardApi?scope=103&format=json&appid=379020&bk_key={kws}&bk_length=600"
    headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
    response = requests.get(url, headers=headers)
    result=response.json()
    filter_dic={k:v for k,v in result.items() if k in ['abstract','url']}
    filter_dic['kws']=kws
    return filter_dic