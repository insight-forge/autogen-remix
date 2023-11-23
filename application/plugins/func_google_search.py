meta_info = {
                "name": "search_google",
                "description": "search the internet If the user's intention is to try to obtain real-time information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "query term for search internet. Please note that query only supports Chinese. if not, it MUST be translated to Chinese",
                        }
                    },
                    "required": ["query"],
                },
            }

def func(**kwargs):
    import requests
    data = kwargs
    url='http://10.60.120.30:8088/google_search'
    response = requests.post(url, data=data)
    result=response.json()
    code=result.get('code',-1)
    if code==0:
        return {'title':result.get('title',''),
                'des':result.get('des',''),
                'query':data.get('query',''),
                'url':result.get('url','')
                }

    return {'title':'',
                'des':result.get('msg','') if len(result.get('msg',''))>0 else 'no search result',
                'query':data.get('query',''),
                'url':''
                }