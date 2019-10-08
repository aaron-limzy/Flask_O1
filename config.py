import os


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or "lalala-We-don't-know-what-it-isss"
    SQLALCHEMY_DATABASE_URI ='mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/aaron'

    SQLALCHEMY_BINDS = {
        'test': 'mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/test',
        'live1': 'mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/live1',
        'live2': 'mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/live2',
        'live3': 'mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/live3',
        'live5': 'mysql+pymysql://mt4:1qaz2wsx@192.168.64.73/live5'
    }

    # Don't need to signal the app whenever there is a change.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE = 300

    UPLOAD_FOLDER = '/path/to/the/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    UPLOADS_DEFAULT_DEST='./project/static/Files/'
    UPLOADS_DEFAULT_URL= 'http://localhost:5000/static/Files/'

    UPLOADED_SWAPS_DEST='./project/static/vantage_swap/'
    UPLOADED_SWAPS_URL='http://localhost:5000/static/vantage_swap/'
    VANTAGE_UPLOAD_FOLDER="./Swaps/Vantage_upload/"

    # To send email when there are server issues.
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['aaron.lim@blackwellglobal.com']






