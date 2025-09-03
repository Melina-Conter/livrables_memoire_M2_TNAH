from ..app import app, db
from sqlalchemy import Column, Integer, String, Date, DateTime, JSON

class Constituent(db.Model):
    __bind_key__ = 'donnees_TMS'
    """
    Une classe pour représenter la table tms-constituent_constituent-description de la base de données.
    
    Attributs
    ---------
    constituentid : sqlalchemy.sql.schema.Column
        Identifiant unique du constituant (clé primaire).
    displayname : sqlalchemy.sql.schema.Column
        Nom d'affichage du constituant.
    autres_labels : sqlalchemy.sql.schema.Column
        Autres labels/étiquettes au format JSON.
    date_naissance_historique : sqlalchemy.sql.schema.Column
        Date de naissance historique.
    date_mort_historique : sqlalchemy.sql.schema.Column
        Date de mort historique.
    date_naissance : sqlalchemy.sql.schema.Column
        Date de naissance (format texte).
    date_mort : sqlalchemy.sql.schema.Column
        Date de mort (format texte).
    activites : sqlalchemy.sql.schema.Column
        Activités au format JSON.
    commune_naissance : sqlalchemy.sql.schema.Column
        Commune de naissance.
    departement_naissance : sqlalchemy.sql.schema.Column
        Département de naissance.
    pays_naissance : sqlalchemy.sql.schema.Column
        Pays de naissance.
    commune_mort : sqlalchemy.sql.schema.Column
        Commune de décès.
    departement_mort : sqlalchemy.sql.schema.Column
        Département de décès.
    pays_mort : sqlalchemy.sql.schema.Column
        Pays de décès.
    biographie : sqlalchemy.sql.schema.Column
        Biographie du constituant.
    roles_creation : sqlalchemy.sql.schema.Column
        Rôles de création au format JSON.
    dossiers_documentation : sqlalchemy.sql.schema.Column
        Dossiers de documentation au format JSON
    db_update : sqlalchemy.sql.schema.Column
        Timestamp de dernière mise à jour.
    """
    __tablename__ = "tms-constituent_constituent-description"
    
    constituentid = db.Column(db.Integer, primary_key=True, nullable=False)
    displayname = db.Column(db.String(300), nullable=True)
    autres_labels = db.Column(db.JSON, nullable=True)
    date_naissance_historique = db.Column(db.Date, nullable=True)
    date_mort_historique = db.Column(db.Date, nullable=True)
    date_naissance = db.Column(db.String(50), nullable=True)
    date_mort = db.Column(db.String(50), nullable=True)
    activites = db.Column(db.JSON, nullable=True)
    commune_naissance = db.Column(db.String(100), nullable=True)
    departement_naissance = db.Column(db.String(100), nullable=True)
    pays_naissance = db.Column(db.String(100), nullable=True)
    commune_mort = db.Column(db.String(100), nullable=True)
    departement_mort = db.Column(db.String(100), nullable=True)
    pays_mort = db.Column(db.String(100), nullable=True)
    biographie = db.Column(db.String(3000), nullable=True)
    roles_creation = db.Column(db.JSON, nullable=True)
    dossiers_documentation = db.Column(db.JSON, nullable=True)
    db_update = db.Column(db.DateTime, nullable=False, default=db.func.now())