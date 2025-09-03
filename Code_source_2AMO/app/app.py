from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

app = Flask(
    __name__, 
    template_folder='templates',
    static_folder='static')
app.config.from_object(Config)


app.name = '2AMO'
db = SQLAlchemy(app)

login = LoginManager(app)
login.login_message = "Vous devez être connecté pour afficher cette page."
csrf = CSRFProtect(app)
csrf.init_app(app)

from .routes import generales, validation
#ne pas oublier d'ajouter les autres .py de /routes lorsque complétés