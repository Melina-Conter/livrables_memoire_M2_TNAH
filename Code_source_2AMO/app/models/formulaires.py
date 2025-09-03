from ..app import app , db
from flask_wtf import FlaskForm
from wtforms import SelectField, FieldList, DateField, TimeField, SubmitField, StringField, PasswordField, SelectMultipleField
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms.widgets import ListWidget, CheckboxInput
import json

class Connexion(FlaskForm):
    """
    Une classe héritant de FlaskForm pour créer un formulaire de connexion pour les utilisateurs déjà inscrit.

    Attributs 
    ---------
    email : Stringfield
        Champ pour soumettre l'email de l'utilisateur.
    password : PasswordField
        Champ pour soumettre le mot de passe de l'utilisateur.

    Exceptions
    ----------
    - Si le mail ou le mot de passe n'a pas été renseigné
    - Si le mot de passe contient moins de 6 caractères
    """
    email=StringField("email", validators=[DataRequired(message="Aucune adresse email n'a été renseignée."), Email()])
    password=PasswordField("password", validators=[DataRequired(message="Aucun mot de passe n'a été renseigné."), Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères.")])

class AjoutUtilisateur(FlaskForm):
    """
    Une classe héritant de FlaskForm pour créer un formulaire d'inscription pour les utilisateurs qui ne se sont pas encore inscrit.

    Attributs 
    ---------
    email : Stringfield
        Champ pour soumettre l'email de l'utilisateur.
    password : PasswordField
        Champ pour soumettre le mot de passe de l'utilisateur.

        Exceptions
    ----------
    - Si le mail ou le mot de passe n'a pas été renseigné
    - Si le mot de passe contient moins de 6 caractères
    """
    password = PasswordField("password", validators=[DataRequired(message="Aucun mot de passe n'a été renseigné."), Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères.")])
    email=StringField("email", validators=[DataRequired(message="Aucune adresse email n'a été renseignée."), Email(message="Veuillez entrer une adresse email valide.")])

class ChangerMdp(FlaskForm):
    """
    Une classe héritant de FlaskForm pour créer un formulaire de changement de mot de passe pour les utilisateurs qui se sont déjà inscrits. 

    Attributs 
    ---------
    email : Stringfield
        Champ pour soumettre l'email de l'utilisateur.
    new_password : PasswordField
        Champ pour soumettre le nouveau mot de passe de l'utilisateur.
    confirmation_mdp : PasswordField
        Champ pour soumettre la confirmation du nouveau mot de passe de l'utilisateur.
    
    Exceptions
    ----------
    - Si le mail ne correspond à aucun utilisateur enregistré.
    - Si le mail, le new_password ou le confirmation_mdp ne sont pas renseignés.
    - Si le new_password contient moins de six caractères
    - Si le confirmation_mdp n'est pas identique au new_password
    """
    email=StringField("email", validators=[DataRequired(message="Aucune adresse email n'a été renseignée."), Email(message="Veuillez entrer une adresse email valide.")])
    new_password = PasswordField("password", validators=[DataRequired(message="Aucun mot de passe n'a été renseigné."), Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères.")])
    confirmation_mdp = PasswordField("conf_password", validators=[DataRequired(message="Aucun mot de passe n'a été renseigné."), EqualTo("new_password", message="Les mots de passe ne correspondent pas")])

from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, SubmitField

class Preferences(FlaskForm):
    """
    Formulaire pour gérer les préférences de domaines TMS de l'utilisateur connecté.
    """
    domaines_entites_tms = SelectMultipleField(
        'Domaines de préférence',
        choices=[
            ('tous', 'Tous'),
            ('architecture', 'Architecture'),
            ('arts décoratifs', 'Arts décoratifs'),
            ('autres', 'Autres'),
            ('peinture', 'Peinture'),
            ('photographie', 'Photographie'),
            ('sculpture', 'Sculpture')
        ],
        option_widget=CheckboxInput(),  # pour une case à cocher par option
        widget=ListWidget(prefix_label=False)  # affiche la liste verticalement
    )
    submit = SubmitField('Valider')

    # Dans votre classe Preferences, ajoutez du debug :
    def set_preferences_utilisateur(self, utilisateur):
        try:
            prefs = utilisateur.preferences if utilisateur.preferences else ["tous"]
            self.domaines_entites_tms.data = prefs
            print(f"Préférences chargées : {prefs}")
        except Exception as e:
            print(f"Erreur chargement préférences : {e}")
            self.domaines_entites_tms.data = ["tous"]
