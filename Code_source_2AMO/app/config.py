import dotenv
from dotenv import load_dotenv
import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config():
    DEBUG = os.environ.get("DEBUG")
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_BINDS = {
        "donnees_TMS": os.getenv('SQLALCHEMY_BINDS_DONNEES_TMS'),
    }
    ACTIONS_PER_PAGE = int(os.environ.get("ACTIONS_PER_PAGE")) # variable pour la pagination de l'historique des actions
    SECRET_KEY = os.environ.get("SECRET_KEY")
    WTF_CSRF_ENABLE = os.environ.get("WTF_CSRF_ENABLE")
    TIMER_INACTIVITE_MINUTES = int(os.getenv("TIMER_INACTIVITE_MINUTES"))
    PERMANENT_SESSION_LIFETIME = timedelta(
            minutes=int(os.environ.get("PERMANENT_SESSION_LIFETIME_MINUTES"))
        )
    SESSION_PERMANENT = os.environ.get("SESSION_PERMANENT")

