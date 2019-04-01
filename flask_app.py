from flask import Flask, request
import logging
import json
import calendar
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
sessionStorage = {}

now_command = 'nothing'
stage = 1


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


def handle_dialog(req, res):
    global now_command, stage
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
                      '"Удалить экскурсию <номер экскурсии>",\n"Редактировать экскурсию <номер экскурсии>",\n"Добавить экскурсию"'
        res['response']['buttons'] = get_suggests(user_id)
        return
    if req['request']['command'].lower() == 'добавить экскурсию' and now_command != 'add excursion':
        now_command = 'add excursion'
        if stage == 1:
            res['response']['text'] = 'Укажите точный адрес начала экскурсии'
            return
    if now_command == 'add excursion':
        if stage == 1:
            address = get_address(req)
            if address:
                res['response']['text'] = 'Ваш адрес распознан. Это ' + address + '. Теперь введите точную дату проведения экскурсии'
                stage += 1
            else:
                res['response']['text'] = 'Введенный адрес некорректен или недостаточно точен. Повторите попытку'
            return
        elif stage == 2:
            date = get_date(req)
            if (date - datetime.utcnow()).days >= 0:
                res['response']['text'] = 'Вот дата ' + str(date)
            else:
                res['response']['text'] = 'Введите дату еще раз'


def get_date(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.DATETIME':
            now_date = datetime.now()
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
            return address[:-2]
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
