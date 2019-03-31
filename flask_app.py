from flask import Flask, request
import logging
import json

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
sessionStorage = {}


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
