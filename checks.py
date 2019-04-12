from datetime import datetime, timedelta, timezone
from string import ascii_letters
import calendar


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
            if 'last_name' in entity['value']:
                name += entity['value']['last_name'][0].upper() + entity['value']['last_name'][1:] + ' '
            else:
                return ['Фамилия не распознана. Повторите ввод', False]
            if 'first_name' in entity['value']:
                name += entity['value']['first_name'][0].upper() + entity['value']['first_name'][1:] + ' '
            else:
                return ['Имя не распознано. Повторите ввод', False]
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
