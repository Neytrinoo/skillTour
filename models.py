from flask_app import app, db
from werkzeug.security import generate_password_hash, check_password_hash


class Excursion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(300))
    date = db.Column(db.DateTime)
    password_hash = db.Column(db.String(400))
    name = db.Column(db.String(150))
    excursion_name = db.Column(db.String(200))
    excursion_description = db.Column(db.String(1500))
    excursion_duration = db.Column(db.String(20))
    place_description = db.Column(db.String(500))
    currency = db.Column(db.String(10))
    sile = db.Column(db.String(8))
    telephone_number = db.Column(db.String(30))
    number = db.Column(db.Integer)
    city = db.Column(db.String(100))
    pt = db.Column(db.String(100))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __str__(self):
        duration = '0' * (2 - len(str(self.excursion_duration).split(':')[0])) + str(self.excursion_duration).split(':')[0] + ':' + \
                   '0' * (2 - len(str(self.excursion_duration).split(':')[1])) + str(self.excursion_duration).split(':')[1]
        result = 'Название экскурсии: ' + self.excursion_name + '\n' + 'Адрес проведения: ' + self.address + '\n' + 'Дата проведения: ' + str(self.date.strftime('%d.%m.%Y %H:%M')) \
                 + '\n' + 'Конкретное описание места встречи: ' + self.place_description + '\n' + 'Экскурсовод: ' + self.name + '\n' + 'Описание экскурсии:' + '\n"' + \
                 self.excursion_description + '"\n' + 'Средняя продолжительность экскурсии: ' + duration + ' (hh:mm)\n'
        currency = ''
        if self.currency == 'рубль':
            currency = '₽'
        elif self.currency == 'евро':
            currency = '€'
        elif self.currency == 'доллар':
            currency = '$'
        result += 'Цена: ' + str(self.sile) + ' ' + currency + '\n' + 'Телефон экскурсовода: ' + str(self.telephone_number)
        return result
