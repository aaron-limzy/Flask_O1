from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_uploads import UploadSet, IMAGES, configure_uploads
import flask_excel as excel
from flask_login import LoginManager, UserMixin, login_required
from werkzeug.security import generate_password_hash
import os

import logging
from logging.handlers import SMTPHandler


app = Flask(__name__)
#app = Flask("Main")
app.config.from_object(Config)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
excel.init_excel(app)
login = LoginManager(app)
login.login_view = 'login'
# Configure the image uploading via Flask-Uploads
excel_format = UploadSet('files',  extensions=('xls', 'xlsx', 'csv'))
configure_uploads(app, excel_format)

if app.config['VANTAGE_UPLOAD_FOLDER']:
    folders = [a for a in app.config['VANTAGE_UPLOAD_FOLDER'].split("/") if (a != "" and a != ".") ]
    for i, folder in enumerate(folders):
        folder = "/".join(folders[:i + 1])  # WE Want the current one as well.
        if os.path.isdir(folder) == False:
            os.mkdir(folder)

from app import routes, errors



if not app.debug:
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Risk-Flask Failure.',
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)



#import pyexcel
#result = db.engine.execute("select * from aaron.aaron_buf")
#