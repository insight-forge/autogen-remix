meta_info = {
                "name": "image_generate",
                "description": "generate a image by prompting if the user's intention is to generate an image",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "prompt for generating image. Please note that prompt only supports English. if not, it must be translated to English",
                        }
                    },
                    "required": ["prompt"],
                },
            }

def func(**kwargs):
# 定义目标URL和要发送的数据
    import requests
    data = kwargs
    response = requests.post("http://10.139.17.136:8089/sd_gen", data=data)
    result=response.json()
    if result.get('code',-1)==0:
        return result.get('url')
    else:
        return result.get('msg')