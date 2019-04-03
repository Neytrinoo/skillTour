from requests import post

url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
files = {'file': open('user_default_avatar.png', 'rb')}
print(post(url, files=files, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json())
