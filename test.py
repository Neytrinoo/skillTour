from requests import post
from PIL import Image
import aiohttp
import io

url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
data = aiohttp.FormData()
img = Image.open('аватарка.png')
bytes_io = io.BytesIO()
img.save(bytes_io, format='PNG')
data.add_field('file', bytes_io)
f = open('аватарка.png', 'rb')
headers = {'Content-Type': 'image/png'}
params = {
    'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY',
}
# session = aiohttp.ClientSession()
files = {
    'file': f,
}
# a = session.post(url, json=params, data=data)
# print(a)
print(post(url, json=params, files=files, headers=headers))
f.close()
