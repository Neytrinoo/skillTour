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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
