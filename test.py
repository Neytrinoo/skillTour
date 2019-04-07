from requests import post, get, delete
import asyncio
from threading import Timer, Event, Thread
import requests
from get_params import get_params

url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
# files = {'file': open('user_default_avatar.png', 'rb')}
print(get(url, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).content)
all_image = get(url, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()['images']
# print(delete(url+'/965417/deee16451592b909a362', headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json())
for image in all_image:
    print(delete(url + '/' + image['id'], headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json())
# class MyThread(Thread):
#     def __init__(self, event):
#         Thread.__init__(self)
#         self.stopped = event
#
#     def run(self):
#         while not self.stopped.wait(5):
#             print("my thread")
#             # call a function
#
#
# stopFlag = Event()
# thread = MyThread(stopFlag)
# thread.start()
# this will stop the timer
# stopFlag.set()
# map_api_server = "http://static-maps.yandex.ru/1.x/"
#
#
# def search_city(city):
#     geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
#     geocoder_params = {'geocode': city, 'format': 'json'}
#     response = requests.get(geocoder_api_server, params=geocoder_params)
#     json_response = response.json()
#     longitude, lattitude, w, h = get_params(json_response)
#     return [longitude, lattitude, w, h]
#
#
# def get_map(longitude, lattitude):
#     map_params = {
#         "ll": ",".join([str(longitude), str(lattitude)]),
#         "l": 'sat'
#     }
#     response = requests.get(map_api_server, params=map_params)
#     url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
#     files = {'file': response.content}
#     image = post(url, files=files, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()
#     return image['image']['id']
#
#
# long, lat, w, h = search_city('Прага')
# a = get_map(long, lat)
# print(a)
# def return_one(b):
#     print(b)
#
#
# t = Timer(2, return_one, [12])
# t.start()
