from flask import Flask, request
import logging
import json
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import requests
from requests import post, delete
from get_params import get_params
from checks import *

app = Flask(__name__)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
app.config.from_object(Config)
logging.basicConfig(level=logging.INFO)
sessionStorage = {}
map_api_server = "http://static-maps.yandex.ru/1.x/"
skill_image_url = 'https://dialogs.yandex.net/api/v1/skills/c02896ed-78df-4558-a5a7-4a3a837e3db4/images'
image_to_delete = []
hello_message = 'Привет! Сейчас вы можете найти себе экскурсию в любом месте, или сами добавить экскурсию! У каждой экскурсии есть уникальный номер. ' \
                'По нему ее можно получить, отредактировать и удалить. Для редактирования и удаления нужно знать уникальный пароль, который задается при ' \
                'добавлении. Вы можете найти тут "живую" эксурсию и аудиоэкскурсию. "Живая" экскурсия - эта экскурсия, которую проводит экскурсовод. Тут вы можете найти ' \
                'такие экскурсии, или же добавить, и другие люди смогут к вам прийти. Аудиоэкскурсия - экскурсия без экскурсовода. Вы идете по улице, а я буду рассказывать вам ' \
                'о достопримечательностях в городе. Тут вы также можете добавить аудиоэкскурсии, или прослушать доступные. Чтобы увидеть доступные команды, напишите "помощь"'
help_message = 'Команды для работы с "живыми" экскурсиями:' \
               '\n"Показать все экскурсии",\n"Добавить экскурсию"\n' \
               '"Показать экскурсии в <город>"\n"Города, в которых есть экскурсии" или "В каких городах есть экскурсии?",\nПосле показа экскурсий в каком-то городе, ' \
               'вы можете выполнить следующие команды:\n' \
               '"Показать экскурсию номер <номер экскурсии>",\n "Удалить экскурсию номер <номер экскурсии>",\n' \
               '"Редактировать экскурсию номер <номер экскурсии в этом городе>"\nКоманды для аудиоэкскурсий:\n"Показать все аудиоэкскурсии",\n"Добавить аудиоэкскурсию",\n' \
               '"Показать аудиоэкскурсии в <город>"\n"Города, в которых есть аудиоэкскурсии" или "В каких городах есть аудиоэкскурсии?"\nПосле показа аудиоэкскурсий в каком-то ' \
               'городе, вы можете выполнить следующие команды:\n"Показать аудиоэкскурсию номер <номер экскурсии>"\n"Удалить аудиоэкскурсию номер <номер экскурсии>"\n' \
               '"прослушать аудиоэкскурсию номер <номер_экскурсии>"'
separator = '<1jWz2f3P8ao31BUo>'


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


def get_pt_excursion_in_city(city, what_is):
    if what_is == 'excursion':
        excursions = Excursion.query.filter_by(city=city).all()
        if not excursions:
            return False
        excursions = list(sorted(excursions, key=lambda x: x.date))
        for i in range(len(excursions)):
            if (datetime.utcnow() - excursions[i].date).days > 1:
                Excursion.query.filter_by(id=excursions[i].id).delete()
            else:
                break
        db.session.commit()
        excursions = Excursion.query.filter_by(city=city).all()
        excursions = list(sorted(excursions, key=lambda x: x.date))
    if what_is == 'audioexcursion':
        excursions = AudioExcursion.query.filter_by(city=city).all()
        if not excursions:
            return False
    pt = ''
    for i in range(len(excursions)):
        excursions[i].number = i + 1
        pt += excursions[i].pt + 'pm2blm' + str(i + 1) + '~'
    db.session.commit()
    return pt[:-1]


# Получаем карту и добавляем эту картинку в Алису
def get_map(files):
    image = post(skill_image_url, files=files, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()
    return image['image']['id']


def get_map_image_with_pt(pt):
    map_params = {
        "l": 'sat,skl',
        'pt': pt
    }
    response = requests.get(map_api_server, params=map_params)
    print(response.content)
    files = {'file': response.content}
    return files


def get_pt_from_address(address):
    long, lat, w, h = search_city(address)
    return str(long) + ',' + str(lat) + ','


def get_map_with_all_excursion(files):
    image = post(skill_image_url, files=files, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()
    return image['image']['id']


def get_map_image_with_all_excursion(what_is):
    map_params = {
        "l": 'sat,skl',
        'pt': ''
    }
    if what_is == 'excursion':
        for excursion in Excursion.query.all():
            map_params['pt'] += excursion.pt + 'pm2dgl' + '~'
        if map_params['pt'] == '':
            return False
    if what_is == 'audioexcursion':
        for excursion in AudioExcursion.query.all():
            map_params['pt'] += excursion.pt + 'pm2dgl' + '~'
        if map_params['pt'] == '':
            return False
    map_params['pt'] = map_params['pt'][:-1]
    response = requests.get(map_api_server, params=map_params)
    files = {'file': response.content}
    return files


def delete_image(image_id):
    delete(skill_image_url + '/' + image_id, headers={'Authorization': 'OAuth AQAAAAAgVOQPAAT7o0JsAefc8kEZhjW8sz0wMsY'}).json()


def handle_dialog(req, res):
    global image_to_delete
    user_id = req['session']['user_id']

    if req['session']['new']:
        sessionStorage[user_id] = {
            'suggests': [
                "Помощь",
                "Показать все экскурсии",
                "Добавить экскурсию",
            ]
        }
        sessionStorage[user_id]['now_command'] = False
        res['response']['text'] = hello_message
        res['response']['buttons'] = get_suggests(user_id)
        return
    else:
        if not sessionStorage[user_id]['now_command']:
            sessionStorage[user_id]['suggests'] = ["Помощь",
                                                   "Показать все аудиоэкскурсии",
                                                   "Показать все экскурсии",
                                                   "Добавить экскурсию",
                                                   "Добавить аудиоэкскурсию"]
        else:
            sessionStorage[user_id]['suggests'] = ["Помощь"]
        res['response']['buttons'] = get_suggests(user_id)
    # Удаляем изображения из Алисы, когда они уже использованы
    if image_to_delete:
        for image_id in image_to_delete:
            delete_image(image_id)
        image_to_delete = []
    if 'помощь' == req['request']['original_utterance'].lower():
        res['response']['text'] = help_message
        return
    # Обработка команд с аудиоэкскурсиями

    # Добавление аудиоэкскурсии
    if not sessionStorage[user_id]['now_command'] and ('добавить' in req['request']['nlu']['tokens'] and (
            'аудиоэкскурсию' in req['request']['nlu']['tokens'] or ('аудио' in req['request']['nlu']['tokens'] and 'экскурсии' in req['request']['nlu']['tokens']))):
        sessionStorage[user_id]['now_command'] = 'add audioexcursion'
        sessionStorage[user_id]['stage'] = 1
        res['response']['text'] = 'Укажите точный адрес начала аудиоэкскурсии, чтобы другие пользователи знали, с какого места можно начинать слушать. ' \
                                  'Для того, чтобы выйти из режима добавления, напишите "!выйти"'
        sessionStorage[user_id]['suggests'] = ["Помощь"]
        res['response']['buttons'] = get_suggests(user_id)
        return
    if sessionStorage[user_id]['now_command'] == 'add audioexcursion':
        if '!выйти' == req['request']['original_utterance'].lower().rstrip().lstrip():
            sessionStorage[user_id]['now_command'] = False
            res['response']['text'] = 'Вы вышли из режима добавления. Возвращайтесь сюда снова!'
            sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Добавить экскурсию", "Добавить аудиоэкскурсию"]
            res['response']['buttons'] = get_suggests(user_id)
            return
        if sessionStorage[user_id]['stage'] == 1:
            sessionStorage[user_id]['add_excursion'] = {}
            address = get_address(req)
            if address:
                res['response']['text'] = 'Ваш адрес распознан. Это ' + address[0] + '. Теперь введите ваше ФИО'
                sessionStorage[user_id]['add_excursion']['address'] = address[0]
                sessionStorage[user_id]['add_excursion']['city'] = address[1]
                sessionStorage[user_id]['add_excursion']['pt'] = get_pt_from_address(address[0])
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = 'Введенный адрес некорректен или недостаточно точен. Повторите попытку'
            return
        if sessionStorage[user_id]['stage'] == 2:
            name = check_name(req)
            if name[1]:
                res['response']['text'] = 'Личные данные распознаны. Теперь введите название вашей аудиоэкскурсии. Например, "Прага. Старый город"'
                sessionStorage[user_id]['add_excursion']['name'] = name[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = name[0]
            return
        if sessionStorage[user_id]['stage'] == 3:
            excursion_name = check_excursion_name(req)
            if excursion_name[1]:
                res['response']['text'] = 'Название экскурсии успешно добавлено. Теперь кратко опишите, о чем ваша аудиоэкскурсия. Какие места будут затронуты, ' \
                                          'уникальные особенности вашей аудиоэкскурсии и т.д.'
                sessionStorage[user_id]['add_excursion']['excursion_name'] = excursion_name[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = excursion_name[0]
            return
        if sessionStorage[user_id]['stage'] == 4:
            excursion_description = check_excursion_description(req)
            if excursion_description[1]:
                res['response']['text'] = 'Описание успешно добавлено. Теперь введите ваши контакты, будь то номер телефона, телеграм, e-mail. Нужно для того, чтобы другие ' \
                                          'пользователи могли оставить вам отзыв об аудиоэкскурсии. Если не хотите оставлять контакты, ' \
                                          'напишите любой текст, например, "контактов нет"'
                sessionStorage[user_id]['add_excursion']['excursion_description'] = excursion_description[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = excursion_description[0]
            return
        if sessionStorage[user_id]['stage'] == 5:
            contacts = check_contact_author(req)
            if contacts[1]:
                res['response']['text'] = 'Контакты успешно добавлены. Теперь введите пароль для аудиоэкскурсии, чтобы при желании вы могли ее удалить.'
                sessionStorage[user_id]['add_excursion']['contacts'] = contacts[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = contacts[0]
            return
        if sessionStorage[user_id]['stage'] == 6:
            password_status = check_password(req)
            if password_status[1]:
                res['response']['text'] = 'Пароль успешно добавлен. Теперь самая главная часть. Нужно добавить текст для аудиоэкскурсии. Максимально допустимое количество ' \
                                          'символов в одном сообщении - 970. Поэтому ввод будет осуществляться по частям. Постарайтесь логически отделить части аудиоэкскурсии ' \
                                          'друг от друга, так будет комфортнее ее слушать. Если вы добавили весь текст, просто напишите: "конец", и процесс добавления ' \
                                          'экскурсии будет завершен. После этого другие пользователи смогут ее найти и прослушать. Итак, начинайте ввод текста'
                sessionStorage[user_id]['add_excursion']['password'] = password_status[0]
                sessionStorage[user_id]['stage'] += 1
                sessionStorage[user_id]['add_excursion']['text_audioexcursion'] = ''
            else:
                res['response']['text'] = password_status[0]
            return
        if sessionStorage[user_id]['stage'] == 7:
            if 'конец' == req['request']['original_utterance'].lower().rstrip().lstrip():
                sessionStorage[user_id]['now_command'] = False
                res['response']['text'] = 'Аудиоэкскурсия успешно добавлена. Теперь любой человек сможет ее прослушать. Ура!'
                sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Добавить экскурсию", "Добавить аудиоэкскурсию"]
                res['response']['buttons'] = get_suggests(user_id)
                excursion = AudioExcursion(address=sessionStorage[user_id]['add_excursion']['address'], name=sessionStorage[user_id]['add_excursion']['name'],
                                           excursion_name=sessionStorage[user_id]['add_excursion']['excursion_name'],
                                           excursion_description=sessionStorage[user_id]['add_excursion']['excursion_description'],
                                           contacts=sessionStorage[user_id]['add_excursion']['contacts'], city=sessionStorage[user_id]['add_excursion']['city'],
                                           pt=sessionStorage[user_id]['add_excursion']['pt'], text=sessionStorage[user_id]['add_excursion']['text_audioexcursion'])
                excursion.set_password(sessionStorage[user_id]['add_excursion']['password'])
                db.session.add(excursion)
                db.session.commit()
                return
            text = req['request']['original_utterance']
            if len(text) > 970:
                res['response']['text'] = 'Максимальная длина в 970 символов превышена. Разделите, пожалуйста, этот текст на части.'
                res['response']['buttons'] = get_suggests(user_id)
                return
            sessionStorage[user_id]['add_excursion']['text_audioexcursion'] += text + separator
            res['response']['text'] = 'Часть аудиоэкскурсии успешно добавлена. Если вы добавили весь текст, напишите "конец". Если нет, то просто продолжайте его вводить.'
            return
    # Показ всех аудиоэкскурсий
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and 'все' in req['request']['nlu']['tokens'] and \
            (('экскурсии' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or 'аудиоэкскурсии' in req['request']['nlu']['tokens']) \
            and not sessionStorage[user_id]['now_command']:
        sessionStorage[user_id]['map_image_with_all_audioexcursion'] = get_map_image_with_all_excursion('audioexcursion')
        if sessionStorage[user_id]['map_image_with_all_audioexcursion']:
            res['response']['text'] = 'Напишите "показать", если вы хотите увидеть карту со всеми аудиоэкскурсиями'
            sessionStorage[user_id]['now_command'] = 'get all audioexcursion'
            sessionStorage[user_id]['suggests'] = ["показать", "Помощь"]
            res['response']['buttons'] = get_suggests(user_id)
        else:
            res['response']['text'] = 'Пока что никто не добавил не одной аудиоэкскурсии. Если у вас есть желание провести экскурсию, скорее добавьте ее, сказав' \
                                      '"Добавить аудиоэкскурсию"!'
        return
    if sessionStorage[user_id]['now_command'] == 'get all audioexcursion':
        if 'показать' in req['request']['nlu']['tokens']:
            all_excursion_image_id = get_map_with_all_excursion(sessionStorage[user_id]['map_image_with_all_audioexcursion'])
            res['response']['text'] = 'Теперь вы можете получить все аудиоэкскурсии в конкретном городе, написав "Показать аудиоэкскурсии в название города"'
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Можете получить все экскурсии в конкретном городе, написав "Показать аудиоэкскурсии в <название_города>"'
            res['response']['card']['image_id'] = all_excursion_image_id
            image_to_delete.append(all_excursion_image_id)
            sessionStorage[user_id]['now_command'] = False
            sessionStorage[user_id]['map_image_with_all_audioexcursion'] = 0
        else:
            res['response']['text'] = 'Команда не распознана. Пожалуйста, повторите ввод'
        return
    # Команда показа аудиоэкскурсий в конкретном городе
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and (
            ('экскурсии' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or ('аудиоэкскурсии' in req['request']['nlu']['tokens'])) \
            and not sessionStorage[user_id]['now_command']:
        city = get_city(req)
        if not city:
            res['response']['text'] = 'Город не распознан. Пожалуйста, повторите ввод'
            return
        sessionStorage[user_id]['now_command'] = 'show audioexcursion in city'
        pt = get_pt_excursion_in_city(city, 'audioexcursion')
        if pt:
            sessionStorage[user_id]['map_image_with_pt'] = get_map_image_with_pt(pt)
            sessionStorage[user_id]['count_excursion'] = len(pt.split('~'))
            res['response']['text'] = 'Напишите "показать", если вы хотите увидеть карту с аудиоэкскурсиями'
            sessionStorage[user_id]['suggests'] = ["показать", "Помощь"]
            res['response']['buttons'] = get_suggests(user_id)
            sessionStorage[user_id]['now_city_audioexcursion'] = city
        else:
            res['response']['text'] = 'В данном городе пока что нет аудиоэкскурсий. Но вы можете это исправить, написав "Добавить аудиоэкскурсию"'
            sessionStorage[user_id]['now_command'] = False
        return
    # Процесс показа аудиоэкскурсии в конкретном городе
    if sessionStorage[user_id]['now_command'] == 'show audioexcursion in city':
        if 'показать' in req['request']['nlu']['tokens']:
            image_id = get_map(sessionStorage[user_id]['map_image_with_pt'])
            res['response'][
                'text'] = 'Теперь вы можете получить информацию об аудио экскурсии, прослушать или удалить ее с помощью ее номера, который указан на метках. Достаточно ' \
                          'написать, например: "Покажи аудио экскурсию номер один", и я покажу вам информацию об этой экскурсии. ' \
                          'Количество аудио экскурсий: ' + str(sessionStorage[user_id]['count_excursion'])
            sessionStorage[user_id]['count_excursion'] = 0
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Теперь вы можете получить информацию об аудиоэкскурсии, пролушать или удалить ее с помощью ее номера, который указан на метках.'
            res['response']['card']['image_id'] = image_id
            image_to_delete.append(image_id)
            sessionStorage[user_id]['map_image_with_pt'] = 0
            sessionStorage[user_id]['now_command'] = False
        else:
            res['response']['text'] = 'Команда не распознана. Пожалуйста, повторите ввод'
        return

    # Показ конкретной аудиоэкскурсии
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and (
            ('экскурсию' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or ('аудиоэкскурсию' in req['request']['nlu']['tokens'])) and 'номер' in \
            req['request']['nlu']['tokens'] and not sessionStorage[user_id]['now_command']:
        if 'now_city_audioexcursion' in sessionStorage[user_id] and sessionStorage[user_id]['now_city_audioexcursion']:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер аудиоэкскурсии не распознан'
                return
            now_excursion = AudioExcursion.query.filter_by(city=sessionStorage[user_id]['now_city_audioexcursion'], number=number).first()
            if not now_excursion:
                res['response']['text'] = 'Экскурсии с таким номером нет в данном городе'
                return
            res['response']['text'] = str(now_excursion) + '\n' + 'Если хотите прослушать аудиоэкскурсию, просто скажите "прослушать аудиоэкскурсию номер ' + str(number) + '"'
            return
        else:
            res['response']['text'] = 'Для того, чтобы получить аудиоэкскурсию по номеру, нужно сначало определить, в каком городе мы будем искать аудиоэкскурсии. Для этого ' \
                                      'сначала напишите: "показать аудиоэкскурсии в <название_города>". Можете узнать, в каких городах они есть, сказав ' \
                                      '"В каких городах есть аудиоэкскурсии"'
            return
    # Запуск процесса прослашивания экскурсии
    if 'прослушать' in req['request']['nlu']['tokens'] and (
            ('экскурсию' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or ('аудиоэкскурсию' in req['request']['nlu']['tokens'])) and 'номер' in \
            req['request']['nlu']['tokens'] and not sessionStorage[user_id]['now_command']:
        if 'now_city_audioexcursion' in sessionStorage[user_id] and sessionStorage[user_id]['now_city_audioexcursion']:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер аудиоэкскурсии не распознан'
                return
            now_excursion = AudioExcursion.query.filter_by(city=sessionStorage[user_id]['now_city_audioexcursion'], number=number).first()
            sessionStorage[user_id]['now_command'] = 'listen_excursion'
            sessionStorage[user_id]['stage_listen'] = 0
            sessionStorage[user_id]['text_to_listen'] = now_excursion.text.split(separator)
            sessionStorage[user_id]['suggests'] = ["Помощь", "Дальше", "Стоп"]
            res['response']['buttons'] = get_suggests(user_id)
            res['response']['text'] = 'Теперь вы можете начать прослушивать эту экскурсию. Чтобы начать слушать, скажите "дальше", а чтобы ' \
                                      'остановить прослушивание, скажите "стоп"'
        else:
            res['response']['text'] = 'Вы не выбрали город, чтобы прослушать аудиоэкскурсию. Чтобы это сделать, сначала нужно выбрать город с аудиоэкскурсиями, например, ' \
                                      '"Покажи экскурсии в Москве", и после этого выберите номер экскурсии, которую хотите прослушать, например, "Прослушать экскурсию номер 3"'
        return
    # Процесс прослушивания экскурсии
    if sessionStorage[user_id]['now_command'] == 'listen_excursion':
        if 'стоп' == req['request']['original_utterance'].lower().rstrip().lstrip() or sessionStorage[user_id]['stage_listen'] >= len(
                sessionStorage[user_id]['text_to_listen']) - 1:
            sessionStorage[user_id]['now_command'] = False
            res['response']['text'] = 'Возвращайтесь еще!'
            if sessionStorage[user_id]['stage_listen'] >= len(sessionStorage[user_id]['text_to_listen']) - 1:
                res['response']['text'] = 'Аудиоэкскурсия закончена. Возвращайтесь еще!'
            sessionStorage[user_id]['stage_listen'] = -1
            sessionStorage[user_id]['text_to_listen'] = False
            sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Показать все аудиоэкскурсии", "Добавить экскурсию"]
            res['response']['buttons'] = get_suggests(user_id)
            return
        if 'дальше' == req['request']['original_utterance'].lower().rstrip().lstrip():
            res['response']['text'] = sessionStorage[user_id]['text_to_listen'][sessionStorage[user_id]['stage_listen']] + '\nСкажите "дальше" или "повторить"'
            sessionStorage[user_id]['stage_listen'] += 1
        elif 'повторить' == req['request']['original_utterance'].lower().rstrip().lstrip():
            res['response']['text'] = sessionStorage[user_id]['text_to_listen'][sessionStorage[user_id]['stage_listen'] - 1] + '\nСкажите "дальше" или "повторить"'
        else:
            res['response']['text'] = 'Скажите "дальше", чтобы продолжить прослушивание, или "повторить", чтобы услышать часть аудио экскурсии еще раз'
        sessionStorage[user_id]['suggests'] = ["Помощь", "Дальше", "Повторить"]
        res['response']['buttons'] = get_suggests(user_id)
        return

    if ('города' in req['request']['nlu']['tokens'] or 'городах' in req['request']['nlu']['tokens']) and (
            ('экскурсии' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or ('аудиоэкскурсии' in req['request']['nlu']['tokens'])):
        excursions = AudioExcursion.query.all()
        cities = []
        for excurs in excursions:
            cities.append(excurs.city)
        cities = list(set(cities))
        if cities:
            res['response']['text'] = 'Вот города, в которых есть аудиоэкскурсии:\n' + '\n'.join(cities)
        else:
            res['response']['text'] = 'Пока что никто не добавил не одной аудиоэкскурсии. Если у вас есть желание это сделать, скорее добавьте ее, дав команду ' \
                                      '"Добавить аудиоэкскурсию"!'
        return

    # Удаление аудиоэкскурсии
    if 'удалить' in req['request']['nlu']['tokens'] and (
            ('экскурсию' in req['request']['nlu']['tokens'] and 'аудио' in req['request']['nlu']['tokens']) or ('аудиоэкскурсию' in req['request']['nlu']['tokens'])) and 'номер' in \
            req['request']['nlu']['tokens']:
        if 'now_city_audioexcursion' in sessionStorage[user_id]:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер аудиоэкскурсии не распознан'
                return
            excursion_to_delete = AudioExcursion.query.filter_by(city=sessionStorage[user_id]['now_city_audioexcursion'], number=number).first()
            if not excursion_to_delete:
                res['response']['text'] = 'Аудиоэкскурсии с таким номером в данном городе не существует'
                return
            res['response']['text'] = 'Чтобы удалить данную аудиоэкскурсию, вам нужно подтвердить, что вы ее создатель.' \
                                      ' Для этого введите пароль, который вы указывали при добавлении. Чтобы выйти из удаления, напишите "!выйти"'
            sessionStorage[user_id]['delete_excursion'] = [sessionStorage[user_id]['now_city_audioexcursion'], number]
            sessionStorage[user_id]['now_command'] = 'delete audioexcursion'
            return

    if sessionStorage[user_id]['now_command'] == 'delete audioexcursion':
        password = req['request']['original_utterance']
        if password == '!выйти':
            res['response']['text'] = 'Вы успешно вышли из режима удаления'
            sessionStorage[user_id]['now_command'] = False
            return
        if not AudioExcursion.query.filter_by(city=sessionStorage[user_id]['delete_excursion'][0], number=sessionStorage[user_id]['delete_excursion'][1]).first().check_password(
                password):
            res['response']['text'] = 'Пароль не распознан. Пожалуйста, повторите ввод'
        else:
            AudioExcursion.query.filter_by(city=sessionStorage[user_id]['delete_excursion'][0], number=sessionStorage[user_id]['delete_excursion'][1]).delete()
            db.session.commit()
            res['response']['text'] = 'Аудиоэкскурсия успешно удалена. Добавьте новую, если хотите'
            sessionStorage[user_id]['now_command'] = False
        return

    # Обработка команд с живыми экскурсиями
    if ('города' in req['request']['nlu']['tokens'] or 'городах' in req['request']['nlu']['tokens']) and 'экскурсии' in req['request']['nlu']['tokens']:
        excursions = Excursion.query.all()
        cities = []
        for excurs in excursions:
            cities.append(excurs.city)
        cities = list(set(cities))
        if cities:
            res['response']['text'] = 'Вот города, в которых есть экскурсии:\n' + '\n'.join(cities)
        else:
            res['response']['text'] = 'Пока что никто не добавил не одной экскурсии. Если у вас есть желание провести экскурсию, скорее добавьте ее, дав команду ' \
                                      '"Добавить экскурсию"!'
        return
    # Редактирование экскурсии
    if 'редактировать' in req['request']['nlu']['tokens'] and 'экскурсию' in req['request']['nlu']['tokens'] and 'номер' in req['request']['nlu']['tokens']:
        if 'now_city' in sessionStorage[user_id]:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер экскурсии не распознан'
                return
            excursion_to_edit = Excursion.query.filter_by(city=sessionStorage[user_id]['now_city'], number=number).first()
            if not excursion_to_edit:
                res['response']['text'] = 'Экскурсии с таким номером в данном городе не существует'
                return
            res['response']['text'] = 'Чтобы редактировать данную экскурсию, вам нужно подтвердить, что вы ее создатель.' \
                                      ' Для этого введите пароль, который вы указывали при добавлении. Чтобы выйти из редактирования, напишите "!выйти"'
            sessionStorage[user_id]['edit_excursion'] = [sessionStorage[user_id]['now_city'], number]
            sessionStorage[user_id]['now_command'] = 'edit excursion'
            sessionStorage[user_id]['stage'] = 1
            sessionStorage[user_id]['suggests'] = ["Помощь"]
            res['response']['buttons'] = get_suggests(user_id)
            return
        else:
            res['response']['text'] = 'Чтобы редактировать экскурсию по номеру, для начала выберите город, в котором находится эта экскурсия. ' \
                                      'Например, "показать экскурсии в Москве"'
            return
    # Удаление экскурсии
    if 'удалить' in req['request']['nlu']['tokens'] and 'экскурсию' in req['request']['nlu']['tokens'] and 'номер' in req['request']['nlu']['tokens']:
        if 'now_city' in sessionStorage[user_id]:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер экскурсии не распознан'
                return
            excursion_to_delete = Excursion.query.filter_by(city=sessionStorage[user_id]['now_city'], number=number).first()
            if not excursion_to_delete:
                res['response']['text'] = 'Экскурсии с таким номером в данном городе не существует'
                return
            res['response']['text'] = 'Чтобы удалить данную экскурсию, вам нужно подтвердить, что вы ее создатель.' \
                                      ' Для этого введите пароль, который вы указывали при добавлении. Чтобы выйти из удаления, напишите "!выйти"'
            sessionStorage[user_id]['delete_excursion'] = [sessionStorage[user_id]['now_city'], number]
            sessionStorage[user_id]['now_command'] = 'delete excursion'
            return
    # Комманда добавления экскурсии
    if 'добавить' in req['request']['nlu']['tokens'] and 'экскурсию' in req['request']['nlu']['tokens'] and not sessionStorage[user_id]['now_command']:
        sessionStorage[user_id]['now_command'] = 'add excursion'
        sessionStorage[user_id]['stage'] = 1
        res['response']['text'] = 'Укажите точный адрес начала экскурсии. Для того, чтобы выйти из режима добавления, напишите "!выйти"'
        sessionStorage[user_id]['suggests'] = ["Помощь"]
        res['response']['buttons'] = get_suggests(user_id)
        return
    if sessionStorage[user_id]['now_command'] == 'delete excursion':
        password = req['request']['original_utterance']
        if password == '!выйти':
            res['response']['text'] = 'Вы успешно вышли из режима удаления'
            sessionStorage[user_id]['now_command'] = False
            return
        if not Excursion.query.filter_by(city=sessionStorage[user_id]['delete_excursion'][0], number=sessionStorage[user_id]['delete_excursion'][1]).first().check_password(
                password):
            res['response']['text'] = 'Пароль не распознан. Пожалуйста, повторите ввод'
        else:
            Excursion.query.filter_by(city=sessionStorage[user_id]['delete_excursion'][0], number=sessionStorage[user_id]['delete_excursion'][1]).delete()
            db.session.commit()
            res['response']['text'] = 'Экскурсия успешно удалена. Добавьте новую, если хотите'
            sessionStorage[user_id]['now_command'] = False
        return

    # Процесс редактирования экскурсии
    if sessionStorage[user_id]['now_command'] == 'edit excursion':
        password = req['request']['original_utterance']
        if password == '!выйти':
            res['response']['text'] = 'Вы успешно вышли из режима редактирования'
            sessionStorage[user_id]['now_command'] = False
            sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Добавить экскурсию"]
            res['response']['buttons'] = get_suggests(user_id)
            return
        if sessionStorage[user_id]['stage'] == 1 and not Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0],
                                                                                   number=sessionStorage[user_id]['edit_excursion'][1]).first().check_password(password):
            res['response']['text'] = 'Пароль не распознан. Пожалуйста, повторите ввод'
            return
        else:
            sessionStorage[user_id]['stage'] += 1
        if sessionStorage[user_id]['stage'] == 2:
            res['response']['text'] = 'Теперь вам нужно выбрать, что редактировать. Вот возможные варианты:\n"Адрес",\n"Название",\n"Дата",\n"Описание места встречи",\n' \
                                      '"Имя экскурсовода",\n"Описание",\n"Продолжительность",\n"Цена",\n"Телефон"'
            return
        if 'адрес' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите адрес, на который вы хотите заменить данные'
            sessionStorage[user_id]['edit_status'] = 'address'
            return
        if 'название' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите название, на которое вы хотите заменить данные'
            sessionStorage[user_id]['edit_status'] = 'excursion_name'
            return
        if 'дата' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите дату, на которую вы хотите заменить данные'
            sessionStorage[user_id]['edit_status'] = 'date'
            return
        if 'описание' in req['request']['nlu']['tokens'] and 'места' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите описание, на которое вы хотите заменить данные'
            sessionStorage[user_id]['edit_status'] = 'place_description'
            return
        if 'имя' in req['request']['nlu']['tokens'] and 'экскурсовода' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите имя экскурсовода, на которое вы хотите изменить данные'
            sessionStorage[user_id]['edit_status'] = 'name'
            return
        if 'описание' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите описание, на которое вы хотите изменить данные'
            sessionStorage[user_id]['edit_status'] = 'description'
            return
        if 'продолжительность' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите продолжительность экскурсии, на которое вы хотите изменить данные'
            sessionStorage[user_id]['edit_status'] = 'duration'
            return
        if 'цена' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Для начала укажите валюту: "рубль", "евро", или "доллар"'
            sessionStorage[user_id]['edit_status'] = 'sile'
            return
        if 'телефон' in req['request']['nlu']['tokens']:
            res['response']['text'] = 'Введите номер телефона, на который вы хотите изменить данные'
            sessionStorage[user_id]['edit_status'] = 'phone'
            return

        if sessionStorage[user_id]['edit_status'] == 'phone':
            telephone_number = req['request']['original_utterance']
            Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0],
                                      number=sessionStorage[user_id]['edit_excursion'][1]).first().telephone_number = telephone_number
            db.session.commit()
            res['response']['text'] = 'Номер телефона успешно изменен!'
            return
        if sessionStorage[user_id]['edit_status'] == 'sile':
            if 'edit_excursion_currency' not in sessionStorage[user_id]:
                currency = check_currency(req)
                if currency:
                    sessionStorage[user_id]['edit_excursion_currency'] = currency
                    res['response']['text'] = 'Валюта успешно задана. Теперь укажите стоимость экскурсии в данной валюте'
                    Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().currency = currency
                    db.session.commit()
                else:
                    res['response']['text'] = 'Введенная валюта некорректна. Пожалуйста, повторите попытку'
                return
            sile = check_sile(req)
            if sile:
                res['response']['text'] = 'Отлично! Стоимость экскурсии изменена'
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().sile = sile
                sessionStorage[user_id]['edit_status'] = ''
                db.session.commit()
            else:
                res['response']['text'] = 'Введенная сумма некорректна. Пожалуйста, повторите попытку'
            return
        if sessionStorage[user_id]['edit_status'] == 'duration':
            time = check_excursion_duration(req)
            if time:
                res['response']['text'] = 'Продолжительность успешно изменена'
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().excursion_duration = [
                    str(time[0]), str(time[1])]
                db.session.commit()
                sessionStorage[user_id]['edit_status'] = ''
            else:
                res['response']['text'] = 'Введенная продолжительность некорректна. Пожалуйста, повторите ввод'
            return
        if sessionStorage[user_id]['edit_status'] == 'description':
            description = check_excursion_description(req)
            if not description[1]:
                res['response']['text'] = description[0]
            else:
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().excursion_description = \
                    description[0]
                db.session.commit()
                res['response']['text'] = 'Описание экскурсии успешно изменено'
                sessionStorage[user_id]['edit_status'] = ''
            return
        if sessionStorage[user_id]['edit_status'] == 'name':
            name = check_name(req)
            if not name[1]:
                res['response']['text'] = name[0]
            else:
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().name = name[0]
                db.session.commit()
                res['response']['text'] = 'Имя успешно изменено'
                sessionStorage[user_id]['edit_status'] = ''
            return
        if sessionStorage[user_id]['edit_status'] == 'place_description':
            place_description = check_place_description(req)
            if place_description[1]:
                res['response']['text'] = 'Описание успешно изменено'
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().place_description = \
                    place_description[0]
                sessionStorage[user_id]['edit_status'] = ''
                db.session.commit()
            else:
                res['response']['text'] = place_description[0]
            return
        if sessionStorage[user_id]['edit_status'] == 'date':
            date = get_date(req)
            if not date:
                res['response']['text'] = 'Дата не распознана. Пожалуйста, повторите ввод'
                return
            if (datetime.now(timezone.utc) - date).days < 1:
                res['response']['text'] = 'Дата успешно изменена: ' + date.strftime('%d.%m.%Y, %H:%M')
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().date = date
                sessionStorage[user_id]['edit_status'] = ''
                db.session.commit()
            else:
                res['response']['text'] = 'Введенная дата некорректна. Введите дату еще раз'
            return
        if sessionStorage[user_id]['edit_status'] == 'address':
            address = get_address(req)
            if address:
                res['response']['text'] = 'Ваш адрес распознан. Это ' + address[0]
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().address = address[0]
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().city = address[1]
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().pt = get_pt_from_address(
                    address[0])
                sessionStorage[user_id]['edit_status'] = ''
                db.session.commit()
            else:
                res['response']['text'] = 'Введенный адрес некорректен или недостаточно точен. Повторите попытку'
            return
        if sessionStorage[user_id]['edit_status'] == 'excursion_name':
            excursion_name = check_excursion_name(req)
            if excursion_name[1]:
                res['response']['text'] = 'Название успешно изменено'
                Excursion.query.filter_by(city=sessionStorage[user_id]['edit_excursion'][0], number=sessionStorage[user_id]['edit_excursion'][1]).first().excursion_name = \
                    excursion_name[0]
                sessionStorage[user_id]['edit_status'] = ''
                db.session.commit()
            else:
                res['response']['text'] = excursion_name[0]
            return
        res['response']['text'] = 'Ничего не понятно. Повторите еще раз'
        sessionStorage[user_id]['edit_status'] = ''
        return
    # Показ экскурсии
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and 'экскурсию' in req['request']['nlu']['tokens'] and 'номер' in \
            req['request']['nlu']['tokens']:
        if 'now_city' in sessionStorage[user_id]:
            number = check_sile(req)
            if not number:
                res['response']['text'] = 'Номер экскурсии не распознан'
                return
            now_excursion = Excursion.query.filter_by(city=sessionStorage[user_id]['now_city'], number=number).first()
            if not now_excursion:
                res['response']['text'] = 'Экскурсии с таким номером нет в данном городе'
                return
            res['response']['text'] = str(now_excursion)
            return
        else:
            res['response']['text'] = 'Для того, чтобы получить экскурсию по номеру, нужно сначало определить, в каком городе мы будем искать экскурсии. Для этого сначала ' \
                                      'напишите: "показать экскурсии в <название_города>"'
            return
    # Комманда показа всех экскурсий
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and 'все' in req['request']['nlu']['tokens'] and 'экскурсии' in \
            req['request']['nlu']['tokens'] and not sessionStorage[user_id]['now_command']:
        sessionStorage[user_id]['map_image_with_all_excursion'] = get_map_image_with_all_excursion('excursion')
        if sessionStorage[user_id]['map_image_with_all_excursion']:
            res['response']['text'] = 'Напишите "показать", если вы хотите увидеть карту со всеми экскурсиями'
            sessionStorage[user_id]['now_command'] = 'get all excursion'
            sessionStorage[user_id]['suggests'] = ["показать", "Помощь"]
            res['response']['buttons'] = get_suggests(user_id)
        else:
            res['response']['text'] = 'Пока что никто не добавил не одной экскурсии. Если у вас есть желание провести экскурсию, скорее добавьте ее, дав команду ' \
                                      '"Добавить экскурсию"!'
        return
    if sessionStorage[user_id]['now_command'] == 'get all excursion':
        if 'показать' in req['request']['nlu']['tokens']:
            all_excursion_image_id = get_map_with_all_excursion(sessionStorage[user_id]['map_image_with_all_excursion'])
            res['response']['text'] = 'Теперь вы можете получить все экскурсии в конкретном городе, написав "Показать экскурсии в название города"'
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Можете получить все экскурсии в конкретном городе, написав "Показать экскурсии в <название_города>"'
            res['response']['card']['image_id'] = all_excursion_image_id
            image_to_delete.append(all_excursion_image_id)
            sessionStorage[user_id]['now_command'] = False
            sessionStorage[user_id]['map_image_with_all_excursion'] = 0
        else:
            res['response']['text'] = 'Команда не распознана. Пожалуйста, повторите ввод'
        return
    # Команда показа экскурсий в конкретном городе
    if ('показать' in req['request']['nlu']['tokens'] or 'покажи' in req['request']['nlu']['tokens']) and 'экскурсии' in req['request']['nlu']['tokens'] and not \
            sessionStorage[user_id]['now_command']:
        city = get_city(req)
        if not city:
            res['response']['text'] = 'Город не распознан. Пожалуйста, повторите ввод'
            return
        sessionStorage[user_id]['now_command'] = 'show excursion in city'
        pt = get_pt_excursion_in_city(city, 'excursion')
        if pt:
            sessionStorage[user_id]['map_image_with_pt'] = get_map_image_with_pt(pt)
            sessionStorage[user_id]['count_excursion'] = len(pt.split('~'))
            res['response']['text'] = 'Напишите "показать", если вы хотите увидеть карту с экскурсиями'
            sessionStorage[user_id]['suggests'] = ["показать", "Помощь"]
            res['response']['buttons'] = get_suggests(user_id)
            sessionStorage[user_id]['now_city'] = city
        else:
            res['response']['text'] = 'В данном городе пока что нет экскурсий. Но вы можете это исправить, написав "Добавить экскурсию"'
            sessionStorage[user_id]['now_command'] = False
        return
    # Процесс показа экскурсии в конкретном городе
    if sessionStorage[user_id]['now_command'] == 'show excursion in city':
        if 'показать' in req['request']['nlu']['tokens']:
            image_id = get_map(sessionStorage[user_id]['map_image_with_pt'])
            res['response'][
                'text'] = 'Теперь вы можете получить информацию об экскурсии, удалить ее или отредактировать с помощью ее номера, который указан на метках. Достаточно написать, ' \
                          'например: "Покажи экскурсию номер один", и я покажу вам информацию об этой экскурсии. Количество экскурсий: ' + \
                          str(sessionStorage[user_id]['count_excursion'])
            sessionStorage[user_id]['count_excursion'] = 0
            res['response']['card'] = {}
            res['response']['card']['type'] = 'BigImage'
            res['response']['card']['title'] = 'Теперь вы можете получить информацию об экскурсии, удалить ее или отредактировать с помощью ее номера, который указан на метках'
            res['response']['card']['image_id'] = image_id
            image_to_delete.append(image_id)
            sessionStorage[user_id]['map_image_with_pt'] = 0
            sessionStorage[user_id]['now_command'] = False
        else:
            res['response']['text'] = 'Команда не распознана. Пожалуйста, повторите ввод'
        return
    # Процесс добавления экскурсии
    if sessionStorage[user_id]['now_command'] == 'add excursion':
        if '!выйти' == req['request']['original_utterance'].lower().rstrip().lstrip():
            sessionStorage[user_id]['now_command'] = False
            res['response']['text'] = 'Вы вышли из режима добавления. Возвращайтесь сюда снова!'
            sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Добавить экскурсию"]
            res['response']['buttons'] = get_suggests(user_id)
            return
        if sessionStorage[user_id]['stage'] == 1:
            sessionStorage[user_id]['add_excursion'] = {}
            address = get_address(req)
            if address:
                res['response']['text'] = 'Ваш адрес распознан. Это ' + address[0] + '. Теперь введите точную дату проведения экскурсии'
                sessionStorage[user_id]['add_excursion']['address'] = address[0]
                sessionStorage[user_id]['add_excursion']['city'] = address[1]
                sessionStorage[user_id]['add_excursion']['pt'] = get_pt_from_address(address[0])
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = 'Введенный адрес некорректен или недостаточно точен. Повторите попытку'
            return
        elif sessionStorage[user_id]['stage'] == 2:
            date = get_date(req)
            if not date:
                res['response']['text'] = 'Дата не распознана. Пожалуйста, повторите попытку'
                return
            if (datetime.now(timezone.utc) - date).days < 1:
                res['response']['text'] = 'Вот дата ' + date.strftime('%d.%m.%Y, %H:%M') + '\nТеперь введите пароль для удаления и редактирования экскурсии. Он нужен, ' \
                                                                                           'чтобы никто, кроме Вас, не смог управлять вашей экскурсией.\n' \
                                                                                           'Пароль должен быть длиной не менее 8 символов. Может содержать латинские' \
                                                                                           ' символы, цифры, пробелы и следующие знаки: "_", "-", ".", ",", ":", ";", "@"' \
                                                                                           ', "\'", "\""'
                sessionStorage[user_id]['add_excursion']['date'] = date
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = 'Введенная дата некорректна. Введите дату еще раз'
            return
        elif sessionStorage[user_id]['stage'] == 3:
            password_status = check_password(req)
            if password_status[1]:
                res['response']['text'] = 'Пароль успешно добавлен. Теперь введите ФИО экскурсовода'
                sessionStorage[user_id]['add_excursion']['password'] = password_status[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = password_status[0]
            return
        elif sessionStorage[user_id]['stage'] == 4:
            name = check_name(req)
            if name[1]:
                res['response']['text'] = 'Личные данные распознаны: ' + name[0] + '. Теперь введите название вашей экскурсии. Например, "Прага. Старый город"'
                sessionStorage[user_id]['add_excursion']['name'] = name[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = name[0]
            return
        elif sessionStorage[user_id]['stage'] == 5:
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
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = excursion_name[0]
            return
        elif sessionStorage[user_id]['stage'] == 6:
            excursion_description = check_excursion_description(req)
            if excursion_description[1]:
                res['response']['text'] = 'Описание успешно добавлено. Теперь введите среднюю продолжительность экскурсии. Например "4 часа 30 минут"'
                sessionStorage[user_id]['add_excursion']['excursion_description'] = excursion_description[0]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = excursion_description[0]
            return
        elif sessionStorage[user_id]['stage'] == 7:
            time = check_excursion_duration(req)
            if time:
                res['response']['text'] = 'Продолжительность успешно добавлена. Теперь опишите по-подробнее точное место встречи. Укажите какие-нибудь опознавательные признаки.' \
                                          ' Например, "Большой дуб рядом с трамвайной остановкой"'
                sessionStorage[user_id]['add_excursion']['excursion_duration'] = [str(time[0]), str(time[1])]
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = 'Введенная продолжительность некорректна. Пожалуйста, повторите ввод'
            return
        elif sessionStorage[user_id]['stage'] == 8:
            place_description = check_place_description(req)
            if place_description[1]:
                res['response']['text'] = 'Описание успешно добавлено. Теперь нужно указать стоимость экскурсии. Но для начала выберите валюту: "рубль", "евро", "доллар"'
                sessionStorage[user_id]['add_excursion']['place_description'] = place_description[0]
                sessionStorage[user_id]['stage_sile'] = 1
                sessionStorage[user_id]['stage'] += 1
            else:
                res['response']['text'] = place_description[0]
            return
        elif sessionStorage[user_id]['stage'] == 9:
            if sessionStorage[user_id]['stage_sile'] == 1:
                currency = check_currency(req)
                # Сначала нужно указать валюту: евро, доллар, рубль
                if currency:
                    res['response']['text'] = 'Валюта успешно задана. Теперь укажите стоимость экскурсии в данной валюте'
                    sessionStorage[user_id]['add_excursion']['currency'] = currency
                    sessionStorage[user_id]['stage_sile'] += 1
                else:
                    res['response']['text'] = 'Введенная валюта некорректна. Пожалуйста, повторите попытку'
                return
            elif sessionStorage[user_id]['stage_sile'] == 2:
                # Теперь указываем стоимость
                sile = check_sile(req)
                if sile:
                    res['response']['text'] = 'Отлично! Стоимость задана. Остался последний шаг: укажите номер телефона экскурсовода'
                    sessionStorage[user_id]['stage_sile'] = 1
                    sessionStorage[user_id]['add_excursion']['sile'] = sile
                    sessionStorage[user_id]['stage'] += 1
                else:
                    res['response']['text'] = 'Введенная сумма некорректна. Пожалуйста, повторите попытку'
                return
        elif sessionStorage[user_id]['stage'] == 10:
            telephone_number = req['request']['original_utterance']
            if len(telephone_number) > 100:
                res['response']['text'] = 'Слишком длинный номер. Максимальная длина - 100 символов. Пожалуйста, повторите ввод'
                return
            sessionStorage[user_id]['add_excursion']['telephone_number'] = telephone_number
            res['response']['text'] = 'Отлично! Экскурсия успешно добавлена! Теперь другие пользователи смогут без труда ее найти\n'
            sessionStorage[user_id]['suggests'] = ["Помощь", "Показать все экскурсии", "Добавить экскурсию"]
            res['response']['buttons'] = get_suggests(user_id)
            excursion = Excursion(address=sessionStorage[user_id]['add_excursion']['address'], date=sessionStorage[user_id]['add_excursion']['date'],
                                  name=sessionStorage[user_id]['add_excursion']['name'], excursion_name=sessionStorage[user_id]['add_excursion']['excursion_name'],
                                  excursion_description=sessionStorage[user_id]['add_excursion']['excursion_description'],
                                  excursion_duration=':'.join(sessionStorage[user_id]['add_excursion']['excursion_duration']),
                                  place_description=sessionStorage[user_id]['add_excursion']['place_description'], currency=sessionStorage[user_id]['add_excursion']['currency'],
                                  sile=sessionStorage[user_id]['add_excursion']['sile'], city=sessionStorage[user_id]['add_excursion']['city'],
                                  pt=sessionStorage[user_id]['add_excursion']['pt'], telephone_number=telephone_number)
            excursion.set_password(sessionStorage[user_id]['add_excursion']['password'])
            db.session.add(excursion)
            db.session.commit()
            sessionStorage[user_id]['stage'] = 1
            sessionStorage[user_id]['now_command'] = False
            return
    res['response']['text'] = 'Команда не распознана. Чтобы увидеть список команд, нажмите "Помощь"'
    return


# Функция возвращает две подсказки для ответа.
def get_suggests(user_id):
    session = sessionStorage[user_id]

    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests']
    ]

    sessionStorage[user_id] = session

    return suggests


if __name__ == '__main__':
    app.run()

from models import Excursion, AudioExcursion
