from flask import Flask, request
import logging
import json
import calendar
from datetime import datetime, timedelta, timezone
from string import ascii_letters
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import requests
from requests import post
from get_params import get_params

app = Flask(__name__)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
app.config.from_object(Config)
logging.basicConfig(level=logging.INFO)
sessionStorage = {}
map_api_server = "http://static-maps.yandex.ru/1.x/"

now_command = False
stage = 1
stage_sile = 1


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(request.json, response)

    logging.info('Response: %r', request.json)

    # Преобразовываем в JSON и возвращаем
    return json.dumps(response)


# Поиск координат по названию города
def search_city(city):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
    geocoder_params = {'geocode': city, 'format': 'json'}
    response = requests.get(geocoder_api_server, params=geocoder_params)
    json_response = response.json()
    longitude, lattitude, w, h = get_params(json_response)
    return [longitude, lattitude, w, h]


# Получаем карту и добавляем эту картинку в Алису
def get_map(longitude, lattitude, w, h):
    map_params = {
        "ll": ",".join([str(longitude), str(lattitude)]),
        'spn': ",".join([str(w), str(h)]),
        "l": 'sat,skl'
    }
    response = requests.get(map_api_server, params=map_params)
    url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
    files = {'file': response.content}
    image = post(url, files=files, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()
    return image['image']['id']


def handle_dialog(req, res):
    global now_command, stage, stage_sile
    user_id = req['session']['user_id']

    if req['session']['new']:
        sessionStorage[user_id] = {
            'suggests': [
                "Показать все экскурсии",
                "Показать ближайшие экскурсии",
                "Добавить экскурсию",
            ]
        }
        # Заполняем текст ответа
        res['response'][
            'text'] = 'Привет! Сейчас ты можешь найти себе экскурсию в любом месте, или сам добавить экскурсию! У каждой экскурсии есть уникальный номер. ' \
                      'По нему ее можно получить, отредактировать и удалить. Для редактирования и удаления нужно знать уникальный пароль, который задается при ' \
                      'добавлении. Вот что я могу:\n"Показать все экскурсии", \n' \
                      '"Показать ближайшие экскурсии",\n"Показать экскурсии в <город>",\n"Получить экскурсию <номер экскурсии>",\n' \
                      '"Удалить экскурсию <номер экскурсии>",\n"Редактировать экскурсию <город экскурсии> <номер экскурсии в этом городе>",\n"Добавить экскурсию"'
        res['response']['buttons'] = get_suggests(user_id)
        return
    if 'добавить' in req['request']['nlu']['tokens'] and 'экскурсию' in req['request']['nlu']['tokens'] and not now_command:
        now_command = 'add excursion'
        if stage == 1:
            res['response']['text'] = 'Укажите точный адрес начала экскурсии'
            return
    if 'показать' in req['request']['nlu']['tokens'] and 'экскурсии' in req['request']['nlu']['tokens'] and not now_command:
        city = get_city(req)
        now_command = 'show excursion in city'
        if not city:
            res['response']['text'] = 'Город не распознан. Пожалуйста, повторите ввод'
            return
        sessionStorage[user_id]['long_lat'] = search_city(city)
        res['response']['text'] = 'Напишите "показать", если вы хотите увидеть карту с экскурсиями'
        return

    if now_command == 'show excursion in city':
        if 'показать' in req['request']['nlu']['tokens']:
            res['response']['text'] = 's'
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Да'
            res['response']['card']['image_id'] = get_map(sessionStorage[user_id]['long_lat'][0], sessionStorage[user_id]['long_lat'][1],
                                                          sessionStorage[user_id]['long_lat'][2], sessionStorage[user_id]['long_lat'][3])
            res['response']['text'] = 'Yes'
            del sessionStorage[user_id]['long_lat']
            now_command = False
        else:
            res['response']['text'] = 'Команда не распознана. Пожалуйста, повторите ввод'
        return

    if now_command == 'add excursion':
        if stage == 1:
            sessionStorage[user_id]['add_excursion'] = {}
            address = get_address(req)
            if address:
                res['response']['text'] = 'Ваш адрес распознан. Это ' + address[0] + '. Теперь введите точную дату проведения экскурсии'
                sessionStorage[user_id]['add_excursion']['address'] = address[0]
                sessionStorage[user_id]['add_excursion']['city'] = address[1]
                stage += 1
            else:
                res['response']['text'] = 'Введенный адрес некорректен или недостаточно точен. Повторите попытку'
            return
        elif stage == 2:
            date = get_date(req)
            if date > datetime.now(timezone.utc).astimezone():
                res['response']['text'] = 'Вот дата ' + date.strftime('%d.%m.%Y, %H:%M') + '\nТеперь введите пароль для удаления и редактирования экскурсии. Он нужен, ' \
                                                                                           'чтобы никто, кроме Вас, не смог управлять вашей экскурсией.\n' \
                                                                                           'Пароль должен быть длиной не менее 8 символов. Может содержать латинские' \
                                                                                           ' символы, цифры, пробелы и следующие знаки: "_", "-", ".", ",", ":", ";", "@"' \
                                                                                           ', "\'", "\""'
                sessionStorage[user_id]['add_excursion']['date'] = date
                stage += 1
            else:
                res['response']['text'] = 'Введенная дата некорректна. Введите дату еще раз'
        elif stage == 3:
            password_status = check_password(req)
            if password_status[1]:
                res['response']['text'] = 'Пароль успешно добавлен. Теперь введите ФИО экскурсовода'
                sessionStorage[user_id]['add_excursion']['password'] = password_status[0]
                stage += 1
            else:
                res['response']['text'] = password_status[0]
            return
        elif stage == 4:
            name = check_name(req)
            if name[1]:
                res['response']['text'] = 'Личные данные распознаны: ' + name[0] + '. Теперь введите название вашей экскурсии. Например, "Прага. Старый город"'
                sessionStorage[user_id]['add_excursion']['name'] = name[0]
                stage += 1
            else:
                res['response']['text'] = name[0]
            return
        elif stage == 5:
            excursion_name = check_excursion_name(req)
            if excursion_name[1]:
                res['response']['text'] = 'Название экскурсии успешно добавлено: ' + excursion_name[
                    0] + '\nТеперь кратко опишите, о чем ваша экскурсия. Какие места будут затронуты и ' \
                         'т.д. Например:\n"Экскурсия по Старому городу в Праге - удивительно ' \
                         'захватывающая. Во время экскурсии мы посетим такие знаменитые места, как ' \
                         'Карлов мост, Староместсая площадь с ратушей, Тынский храм и Пороховая башня.' \
                         ' Во время экскурсии будет время сфотографироваться со всеми перечисленными ' \
                         'достопримечательностями, а также будет время перекусить."'
                sessionStorage[user_id]['add_excursion']['excursion_name'] = excursion_name[0]
                stage += 1
            else:
                res['response']['text'] = excursion_name[0]
            return
        elif stage == 6:
            excursion_description = check_excursion_description(req)
            if excursion_description[1]:
                res['response']['text'] = 'Описание успешно добавлено. Теперь введите среднюю продолжительность экскурсии'
                sessionStorage[user_id]['add_excursion']['excursion_description'] = excursion_description[0]
                stage += 1
            else:
                res['response']['text'] = excursion_description[0]
            return
        elif stage == 7:
            time = check_excursion_duration(req)
            if time:
                res['response']['text'] = 'Продолжительность успешно добавлена. Теперь опишите по-подробнее точное место встречи. Укажите какие-нибудь опознавательные признаки.' \
                                          ' Например, "Большой дуб рядом с трамвайной остоновкой"'
                sessionStorage[user_id]['add_excursion']['excursion_duration'] = [str(time[0]), str(time[1])]
                stage += 1
            else:
                res['response']['text'] = 'Введенная продолжительность некорректна. Пожалуйста, повторите ввод'
            return
        elif stage == 8:
            place_description = check_place_description(req)
            if place_description[1]:
                res['response']['text'] = 'Описание успешно добавлено. Теперь нужно указать стоимость экскурсии. Но для начала выберите валюту: "рубль", "евро", "доллар"'
                sessionStorage[user_id]['add_excursion']['place_description'] = place_description[0]
                stage += 1
            else:
                res['response']['text'] = place_description[0]
            return
        elif stage == 9:
            if stage_sile == 1:
                currency = check_currency(req)
                # Сначала нужно указать валюту: евро, доллар, рубль
                if currency:
                    res['response']['text'] = 'Валюта успешно задана. Теперь укажите стоимость экскурсии в данной валюте'
                    sessionStorage[user_id]['add_excursion']['currency'] = currency
                    stage_sile += 1
                else:
                    res['response']['text'] = 'Введенная валюта некорректна. Пожалуйста, повторите попытку'
                return
            elif stage_sile == 2:
                # Теперь указываем стоимость
                sile = check_sile(req)
                if sile:
                    res['response']['text'] = 'Отлично! Стоимость задана. Остался последний шаг: укажите номер телефона экскурсовода'
                    stage_sile = 1
                    sessionStorage[user_id]['add_excursion']['sile'] = sile
                    stage += 1
                else:
                    res['response']['text'] = 'Введенная сумма некорректна. Пожалуйста, повторите попытку'
                return
        elif stage == 10:
            telephone_number = req['request']['original_utterance']
            sessionStorage[user_id]['add_excursion']['telephon_number'] = telephone_number
            res['response']['text'] = 'Отлично! Экскурсия успешно добавлена! Теперь другие пользователи смогут без труда ее найти\n' + str(sessionStorage[user_id]['add_excursion'])
            excursion = Excursion(address=sessionStorage[user_id]['add_excursion']['address'], date=sessionStorage[user_id]['add_excursion']['date'],
                                  name=sessionStorage[user_id]['add_excursion']['name'], excursion_name=sessionStorage[user_id]['add_excursion']['excursion_name'],
                                  excursion_description=sessionStorage[user_id]['add_excursion']['excursion_description'],
                                  excursion_duration=':'.join(sessionStorage[user_id]['add_excursion']['excursion_duration']),
                                  place_description=sessionStorage[user_id]['add_excursion']['place_description'], currency=sessionStorage[user_id]['add_excursion']['currency'],
                                  sile=sessionStorage[user_id]['add_excursion']['sile'], city=sessionStorage[user_id]['add_excursion']['city'])
            excursion.set_password(sessionStorage[user_id]['add_excursion']['password'])
            db.session.add(excursion)
            db.session.commit()
            stage = 1
            res['response']['text'] += str(Excursion.query.filter_by(id=1).first())
            now_command = False
            return


def check_sile(req):
    sile = False
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.NUMBER':
            sile = entity['value']
            if len(str(sile)) > 8:
                return False
            return sile
    return sile


def check_currency(req):
    currency = False
    if 'рубль' in req['request']['nlu']['tokens']:
        currency = 'рубль'
    elif 'доллар' in req['request']['nlu']['tokens'] or 'долар' in req['request']['nlu']['tokens']:
        currency = 'доллар'
    elif 'евро' in req['request']['nlu']['tokens']:
        currency = 'евро'
    return currency


def check_place_description(req):
    place_description = req['request']['original_utterance']
    if len(place_description) > 500:
        return ['Превышено допустимое количество символов: 500. Пожалуйста, повторите ввод', False]
    return [place_description, True]


def check_excursion_duration(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.DATETIME':
            hour = 0
            minute = 0
            if 'hour' in entity['value']:
                hour = entity['value']['hour']
            if 'minute' in entity['value']:
                minute = entity['value']['minute']
            return [hour, minute]
    return False


def check_excursion_description(req):
    excursion_description = req['request']['original_utterance']
    if len(excursion_description) > 1500:
        return ['Превышено допустимое количество символов: 1500. Пожалуйста, повторите ввод', False]
    return [excursion_description, True]


# Проверка введенного названия экскурсии на длину
def check_excursion_name(req):
    excursion_name = req['request']['original_utterance']
    if len(excursion_name) > 200:
        return ['Превышена допустимое количество символов: 200. Пожалуйста, повторите ввод', False]
    return [excursion_name, True]


# Проверка введенного имени экскурсовода
def check_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            name = ''
            if 'first_name' in entity['value']:
                name += entity['value']['first_name'][0].upper() + entity['value']['first_name'][1:] + ' '
            else:
                return ['Имя не распознано. Повторите ввод', False]
            if 'last_name' in entity['value']:
                name += entity['value']['last_name'][0].upper() + entity['value']['last_name'][1:] + ' '
            else:
                return ['Фамилия не распознана. Повторите ввод', False]
            if 'patronymic_name' in entity['value']:
                name += entity['value']['patronymic_name'][0].upper() + entity['value']['patronymic_name'][1:] + ' '
            return [name, True]
    return ['Введенные данные не распознаны. Повторите ввод', False]


# Проверка правильности ввода пароля
def check_password(req):
    valid_characters = list(ascii_letters) + [' ', '_', '-', '.', ',', ':', ';', '@', '\'', '"']
    password = req['request']['original_utterance']
    try:
        if len(password) < 8:
            return ['Пароль слишком короткий. Повторите ввод', False]
        for symbol in password:
            if symbol not in valid_characters and not symbol.isdigit():
                return ['В пароле присутствуют недопустимые символы. Повторите ввод', False]
        return [password, True]
    except Exception as e:
        return ['Введенный пароль некорректен. Повторите ввод', False]


def get_date(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.DATETIME':
            now_date = datetime.now(timezone.utc).astimezone()
            # Если год задан относительно, то добавляем к текущей дате 365 дней. Больше нельзя, т.к. ограничение на дату - год вперед
            if 'year_is_relative' in entity['value']:
                if entity['value']['year_is_relative']:
                    if entity['value']['year'] <= 1:
                        if now_date.year % 4 != 0:
                            now_date += timedelta(days=365)
                        else:
                            now_date += timedelta(days=364)
                else:
                    now_date = now_date.replace(year=entity['value']['year'])

            if 'month_is_relative' in entity['value']:
                if entity['value']['month_is_relative']:
                    if entity['value']['month'] <= 12:  # Ограничение на дату - не больше года вперед
                        for i in range(entity['value']['month']):
                            days_in_month = calendar.monthrange(now_date.year, now_date.month)[1]
                            now_date += timedelta(days=days_in_month)
                    else:
                        return False
                else:
                    now_date = now_date.replace(month=entity['value']['month'])

            if 'day_is_relative' in entity['value']:
                if entity['value']['day_is_relative']:
                    if entity['value']['day'] <= 365:  # Ограничение на дату - не больше года вперед
                        now_date += timedelta(days=entity['value']['day'])
                    else:
                        return False
                else:
                    now_date = now_date.replace(day=entity['value']['day'])
            if 'hour_is_relative' in entity['value']:
                if entity['value']['hour_is_relative']:
                    if entity['value']['hour'] <= 8760:
                        now_date += timedelta(hours=entity['value']['hour'])
                    else:
                        return False
                else:
                    now_date = now_date.replace(hour=entity['value']['hour'])
            if 'minute_is_relative' in entity['value']:
                if entity['value']['minute_is_relative']:
                    if entity['value']['minute'] <= 525600:
                        now_date += timedelta(minutes=entity['value']['minute'])
                    else:
                        return False
                else:
                    now_date = now_date.replace(minute=entity['value']['minute'])
            return now_date
    return False


def get_city(req):
    city = False
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            if 'city' in entity['value']:
                city = entity['value']['city']
                break
            else:
                return False
    return city


def get_address(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            address = ''
            if 'country' in entity['value']:
                address += entity['value']['country'] + ', '
            if 'city' in entity['value']:
                address += entity['value']['city'] + ', '
            else:
                return False
            if 'street' in entity['value']:
                address += entity['value']['street'] + ', '
            else:
                return False
            if 'house_number' in entity['value']:
                address += entity['value']['house_number'] + ', '
            return [address[:-2], entity['value']['city']]
    return False


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id):
    session = sessionStorage[user_id]

    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests'][:2]
    ]

    sessionStorage[user_id] = session

    return suggests


if __name__ == '__main__':
    app.run()

from models import Excursion
