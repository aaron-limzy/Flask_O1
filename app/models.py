
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_login import LoginManager, UserMixin, login_required, AnonymousUserMixin
from app import login

class User(UserMixin):

    # user_database = {"JohnDoe": ("JohnDoe", "John" , "john@john.com", "123"),
    #            "JaneDoe": ("JaneDoe", "Jane", "jane@jane.com", "123"),
    #                  "aaron": ("aaron", "aaron_lzy", "jane@jane.com", 'pbkdf2:sha256:50000$jNbCcEO7$c683186eb6c53fdb3b111e194e2598ea902eb049bf64d6a8d989c7e2c447cc92')
    #                  }

    id = ""
    email = ""
    admin_rights = 0
    password_hash = "asdf"

    #password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.id)

    def __init__(self, username, email, password_hash, admin_rights):
        self.id = username
        self.email = email
        self.admin_rights = admin_rights
        self.password_hash = password_hash


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)
    #
    # @classmethod
    # def get(cls, id):
    #     print(id)
    #     return cls.user_database.get(id)


@login.user_loader
def load_user(username):
    #print("Load User {}".format(username))
    sql_return_obj = db.engine.execute("select * from aaron.flask_login where username='{}'".format(username))
    sql_return_keys = sql_return_obj.keys()
    sql_return_val = sql_return_obj.fetchall()

    if len(sql_return_val) == 0:
        return None
    else:
        user_info = dict(zip(sql_return_keys, sql_return_val[0]))
        return User(username=user_info["username"],     # Make the user and return it.
                    email=user_info["email"],
                    password_hash=user_info["password_hash"],
                    admin_rights=user_info["admin_rights"])



class flask_users(db.Model, UserMixin):

    username = db.Column(db.String(15), primary_key=True, unique=True)
    email = db.Column(db.String(255), unique=True)
    admin_rights = db.Column(db.Integer)
    password_hash = db.Column(db.String(255))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def __init__(self, username, email, password_hash, admin_rights):
        self.username = username
        self.email = email
        self.admin_rights = admin_rights
        self.password_hash = password_hash


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)
    #
    # @classmethod
    # def get(cls, id):
    #     print(id)
    #     return cls.user_database.get(id)
