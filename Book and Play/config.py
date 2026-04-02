import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-tc-losheim-2026')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'bookandplay.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None  # CSRF tokens don't expire


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
