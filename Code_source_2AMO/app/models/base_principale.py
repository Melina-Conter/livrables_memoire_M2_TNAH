from ..app import app, db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Text, text
from sqlalchemy.dialects.postgresql import JSON, JSONB

class TableTMS(db.Model):
    """
    Une classe pour représenter la table app_alignement.table_tms.
    Attributs
    ---------
    tms_id : sqlalchemy.sql.schema.Column
        Identifiant unique de l'entité TMS (clé primaire).
    nb_roles_creation : sqlalchemy.sql.schema.Column
        Nombre de rôles de création associés.
    statut_validation : sqlalchemy.sql.schema.Column
        Statut de validation du TMS.
    displayname : sqlalchemy.sql.schema.Column
        Nom d'affichage du TMS.
    verrouille_par : sqlalchemy.sql.schema.Column
        Identifiant de l'utilisateur qui a verrouillé le TMS (clé étrangère).
    date_heure_verrouillage : sqlalchemy.sql.schema.Column
        Date et heure du verrouillage de l'entité TMS.
    dossiers_documentation : sqlalchemy.sql.schema.Column
        Dossiers de documentation associés à l'entité TMS (au format JSONB).
    """
    __tablename__ = "table_tms"
    tms_id = db.Column(db.Integer, primary_key=True, nullable=False)
    nb_roles_creation = db.Column(db.Integer, nullable=True)
    statut_validation = db.Column(db.String(20), nullable=True)
    displayname = db.Column(db.Text, nullable=True)
    verrouille_par = db.Column(db.Integer, db.ForeignKey('utilisateurs.id_utilisateur'), nullable=True)
    date_heure_verrouillage = db.Column(db.DateTime, nullable=True)
    dossiers_documentation =db.Column(JSONB, nullable=True)

    # relations 
    utilisateur_verrou = db.relationship("Utilisateurs", backref="tms_verrouilles", foreign_keys=[verrouille_par])

    @staticmethod
    def changer_statut_validation(tms_id, nouveau_statut):
        """
        Change le statut de validation d'une entité TMS.
        
        Args:
            tms_id (int): Identifiant de l'entité TMS
            nouveau_statut (str): Nouveau statut à appliquer
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Récupération de l'entité TMS
            entite_tms = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
            
            if not entite_tms:
                return False, "Entité TMS introuvable"
            
            # Mise à jour du statut
            entite_tms.statut_validation = nouveau_statut
            
            # Validation en base
            db.session.commit()
            
            return True, f"Statut changé vers '{nouveau_statut}' avec succès"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors du changement de statut : {str(e)}"


class TableCandidats(db.Model):
    """
    Une classe pour représenter la table app_alignement.table_candidats.
    Attributs
    ---------
    qid : sqlalchemy.sql.schema.Column
        Identifiant Wikidata du candidat (clé unique).
    type_candidat : sqlalchemy.sql.schema.Column
        Type de candidat.
    nb_id_externes : sqlalchemy.sql.schema.Column
        Nombre d'identifiants externes.
    id_candidat : sqlalchemy.sql.schema.Column
        Identifiant interne du candidat (clé primaire).
    label : sqlalchemy.sql.schema.Column
        Libellé du candidat.
    """
    __tablename__ = "table_candidats"
    id_candidat = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    qid = db.Column(db.String(20), unique=True, nullable=False)
    type_candidat = db.Column(db.String(20), nullable=True)
    nb_id_externes = db.Column(db.Integer, nullable=True)
    label = db.Column(db.Text, nullable=True)

class Utilisateurs(UserMixin, db.Model):
    """
    Une classe pour représenter la table app_alignement.utilisateurs.
    Attributs
    ---------
    id_utilisateur : sqlalchemy.sql.schema.Column
        Identifiant de l'utilisateur (clé primaire, auto-incrémenté).
    email : sqlalchemy.sql.schema.Column
        Adresse email de l'utilisateur.
    mdp : sqlalchemy.sql.schema.Column
        Mot de passe (hashé).
    date_heure_creation : sqlalchemy.sql.schema.Column
        Timestamp de création du compte.
    preferences : sqlalchemy.sql.schema.Column
        Préférences de l'utilisateur (par défaut: 'tous').
    """
    __tablename__ = "utilisateurs"
    
    id_utilisateur = db.Column(db.BigInteger, primary_key=True, autoincrement=True, nullable=False)
    email = db.Column(db.String(320), nullable=False)
    mdp = db.Column(db.Text, nullable=False)
    date_heure_creation = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=True)
    preferences = db.Column(db.JSON, server_default=text("'[\"tous\"]'::json"), nullable=True)
    
    @staticmethod
    def identification(email, password):
        utilisateur = Utilisateurs.query.filter(
            Utilisateurs.email == email
        ).first()
        
        if utilisateur and check_password_hash(utilisateur.mdp, password):
            return utilisateur
        return None
    
    @staticmethod
    def ajout(email, password):
        erreurs = []
        
        unique_mail = Utilisateurs.query.filter(
            Utilisateurs.email == email
        ).count()
        if unique_mail > 0:
            erreurs.append("Cette adresse email a déjà été utilisée")
            
        if len(erreurs) > 0:
            print(f"Erreur.s rencontrée.s : {erreurs}")
            return False, erreurs
            
        utilisateur = Utilisateurs(
            email=email,
            mdp=generate_password_hash(password)
        )
        try:
            db.session.add(utilisateur)
            db.session.commit()
            print("Ajout réussi !")
            return True, utilisateur
        except Exception as erreur:
            return False, [str(erreur)]
    
    def get_id(self):
        return self.id_utilisateur
    
    @login.user_loader
    def get_user_by_id(id):
        return Utilisateurs.query.get(int(id))

    def get_preferences(self):
        return self.preferences    

class RelationsTMSCandidats(db.Model):
    """
    Une classe pour représenter la table app_alignement.relations_tms_candidats.
    
    Attributs
    ---------
    id_match : sqlalchemy.sql.schema.Column
        Identifiant de la relation (clé primaire).
    tms_id : sqlalchemy.sql.schema.Column
        Référence au TMS concerné (clé étrangère).
    qid : sqlalchemy.sql.schema.Column
        Référence au candidat concerné (clé étrangère).
    score_api : sqlalchemy.sql.schema.Column
        Score fourni par l'API.
    score_flag : sqlalchemy.sql.schema.Column
        Indicateur de qualité globale de la correspondance.
    score_flag_date_naissance : sqlalchemy.sql.schema.Column
        Indicateur de qualité pour la correspondance de la date de naissance.
    score_flag_date_mort : sqlalchemy.sql.schema.Column
        Indicateur de qualité pour la correspondance de la date de mort.
    score_flag_lieu_naissance : sqlalchemy.sql.schema.Column
        Indicateur de qualité pour la correspondance du lieu de naissance.
    score_flag_lieu_mort : sqlalchemy.sql.schema.Column
        Indicateur de qualité pour la correspondance du lieu de mort.
    score_flag_nom : sqlalchemy.sql.schema.Column
        Indicateur de qualité pour la correspondance du nom.
    """
    
    __tablename__ = "relations_tms_candidats"

    # Colonnes existantes
    id_match = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    tms_id = db.Column(db.Integer, db.ForeignKey('table_tms.tms_id'), nullable=False)
    qid = db.Column(db.String(20), db.ForeignKey('table_candidats.qid'), nullable=False)
    score_api = db.Column(db.Numeric, nullable=True)
    score_flag = db.Column(db.Integer, nullable=True)
    score_flag_date_naissance = db.Column(db.Integer, nullable=True)
    score_flag_date_mort = db.Column(db.Integer, nullable=True)
    score_flag_lieu_naissance = db.Column(db.Integer, nullable=True)
    score_flag_lieu_mort = db.Column(db.Integer, nullable=True)
    score_flag_nom = db.Column(db.Integer, nullable=True)
    
    # Relations
    tms = db.relationship("TableTMS", backref="relations")
    candidat = db.relationship("TableCandidats", backref="relations")

class LieuxCandidats(db.Model):
    
    """
    Une classe pour représenter la table app_alignement.lieux_candidats.

    Attributs
    ---------
    id_lieu : sqlalchemy.sql.schema.Column
        Identifiant du lieu (clé primaire).
    qid : sqlalchemy.sql.schema.Column
        Référence au candidat concerné (clé étrangère).
    type_lieu : sqlalchemy.sql.schema.Column
        Type du lieu (naissance, mort, etc.).
    nom_lieu : sqlalchemy.sql.schema.Column
        Nom du lieu.
    rang_lieu : sqlalchemy.sql.schema.Column
        Rang hiérarchique ou précision du lieu.
    """
    __tablename__ = "lieux_candidats"

    id_lieu = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    qid = db.Column(db.String(20), db.ForeignKey('table_candidats.qid'), nullable=True)
    type_lieu = db.Column(db.String(20), nullable=True)
    nom_lieu = db.Column(db.Text, nullable=True)
    rang_lieu = db.Column(db.String(30), nullable=True)

    candidat = db.relationship("TableCandidats", backref="lieux")

class Historique(db.Model):
    
    """
    Une classe pour représenter la table app_alignement.historique.

    Attributs
    ---------
    id_historique : sqlalchemy.sql.schema.Column
        Identifiant de l'action (clé primaire).
    id_utilisateur : sqlalchemy.sql.schema.Column
        Référence à l'utilisateur (clé étrangère).
    id_match : sqlalchemy.sql.schema.Column
        Référence à la correspondance TMS/candidat (clé étrangère).
    date_heure_action : sqlalchemy.sql.schema.Column
        Date et heure de l'action.
    action : sqlalchemy.sql.schema.Column
        Type d'action effectuée.
    """
    __tablename__ = "historique"

    id_historique = db.Column(db.BigInteger, primary_key=True, autoincrement=True, nullable=False)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('utilisateurs.id_utilisateur', ondelete="CASCADE"), nullable=True)
    id_match = db.Column(db.Integer, db.ForeignKey('relations_tms_candidats.id_match'), nullable=True)
    date_heure_action = db.Column(db.DateTime, server_default=db.func.now(), nullable=True)
    action = db.Column(db.String(20), nullable=False)

    utilisateur = db.relationship("Utilisateurs", backref="actions")
    match = db.relationship("RelationsTMSCandidats", backref="historique")

    #Méthode pour enregistrer l'action "valider" d'une entité TMS dans l'historique
    @staticmethod
    def enregistrer_validation_candidats(tms_id, qids_selectionnes, id_utilisateur):
        """
        Enregistre la validation/refus de candidats dans l'historique.
    
        Pour chaque candidat correspondant au tms_id :
        - Si le QID est dans qids_selectionnes : crée une entrée "valide"
        - Si le QID n'est pas dans qids_selectionnes : crée une entrée "refuse"
    
        Args:
            tms_id (int): Identifiant de l'entité TMS
            qids_selectionnes (list): Liste des QIDs des candidats sélectionnés
            id_utilisateur (int): Identifiant de l'utilisateur qui effectue l'action
        
        Returns:
            tuple: (success: bool, message: str, dict: {'valides': int, 'refuses': int})
        """
        try:
            # Récupération de toutes les relations pour l'entité TMS
            relations = db.session.query(RelationsTMSCandidats).filter(
                RelationsTMSCandidats.tms_id == tms_id
            ).all()
        
            if not relations:
                return False, "Aucune relation trouvée pour cette entité TMS", {'valides': 0, 'refuses': 0}
        
            # Création d'une entrée historique pour chaque relation
            nb_validations = 0
            nb_refus = 0
            
            for relation in relations:
                # Déterminer l'action selon si le QID est sélectionné ou non
                action = "valide" if relation.qid in qids_selectionnes else "refuse"
                
                historique_entry = Historique(
                    id_utilisateur=id_utilisateur,
                    id_match=relation.id_match,
                    action=action
                )
                db.session.add(historique_entry)
                
                if action == "valide":
                    nb_validations += 1
                else:
                    nb_refus += 1
        
            # Libère le verrou
            tms = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
            if tms:
                tms.verrouille_par = None
                tms.date_heure_verouillage = None

            # Validation en base
            db.session.commit()
            
            total = nb_validations + nb_refus
            message = f"Traitement terminé : {nb_validations} candidat(s) validé(s), {nb_refus} candidat(s) refusé(s) (total: {total})."
        
            return True, message, {'valides': nb_validations, 'refuses': nb_refus}
        
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de l'enregistrement : {str(e)}", {'valides': 0, 'refuses': 0}

    #Methode pour enregistrer l'action "refuser" pour tous les candidats d'une entité TMS dans l'historique
    @staticmethod
    def enregistrer_refus_tous_candidats(tms_id, id_utilisateur):
        """
        Enregistre le refus de tous les candidats d'une entité TMS dans l'historique.

        Pour chaque relation TMS-Candidat correspondant au tms_id,
        crée une entrée dans l'historique avec l'action "refuse".

        Args:
            tms_id (int): Identifiant de l'entité TMS
            id_utilisateur (int): Identifiant de l'utilisateur qui effectue l'action
        """
        try:
            # Récupération de toutes les relations pour l'entité TMS
            relations = db.session.query(RelationsTMSCandidats).filter_by(tms_id=tms_id).all()
            
            if not relations:
                return False, "Aucune relation trouvée pour ce TMS", 0
            
            # Création d'une entrée historique pour chaque relation
            nb_relations = 0
            for relation in relations:
                historique_entry = Historique(
                    id_utilisateur=id_utilisateur,
                    id_match=relation.id_match,
                    action="refuse"
                )
                db.session.add(historique_entry)
                nb_relations += 1
            
            # Libère le verrou
            tms = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
            if tms:
                tms.verrouille_par = None
                tms.date_heure_verrouillage = None

            # Validation en base
            db.session.commit()
            
            return True, f"Refus enregistré avec succès pour {nb_relations} candidat(s) wikidata.", nb_relations
            
        except Exception as e:
            db.session.rollback()
            return False, f'''Erreur lors de l'enregistrement de l'action "refuse" dans l'historique : {str(e)}''', 0

    #Methode pour enregistrer l'action "passer" d'une entité TMS dans l'historique
    @staticmethod
    def enregistrer_passage_entite(tms_id, id_utilisateur):
        """
        Enregistre le passage d'une entité TMS dans l'historique.
        
        Pour chaque relation TMS-Candidat correspondant au tms_id,
        crée une entrée dans l'historique avec l'action "passe".
        
        Args:
            tms_id (int): Identifiant de l'entité TMS passée
            id_utilisateur (int): Identifiant de l'utilisateur qui effectue l'action
            
        Returns:
            tuple: (success: bool, message: str, nb_relations: int)
        """
        try:
            # Récupération de toutes les relations pour l'entité TMS
            relations = db.session.query(RelationsTMSCandidats).filter_by(tms_id=tms_id).all()
            
            if not relations:
                return False, "Aucune relation trouvée pour ce TMS", 0
            
            # Création d'une entrée historique pour chaque relation
            nb_relations = 0
            for relation in relations:
                historique_entry = Historique(
                    id_utilisateur=id_utilisateur,
                    id_match=relation.id_match,
                    action="passe"
                )
                db.session.add(historique_entry)
                nb_relations += 1
            
            # Libère le verrou
            tms = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
            if tms:
                tms.verrouille_par = None
                tms.date_heure_verouillage = None

            # Validation en base
            db.session.commit()
            
            return True, f"Passage enregistré avec succès pour {nb_relations} candidat(s) wikidata.", nb_relations
            
        except Exception as e:
            db.session.rollback()
            return False, f'''Erreur lors de l'enregistrement de l'action "passer" dans l'historique : {str(e)}''', 0

    
    @staticmethod
    def annuler_action(tms_id, id_utilisateur, types_actions):
        """
        Annule une ou plusieurs actions liées à une entité TMS pour un utilisateur donné.
        Supprime aussi le statut de validation dans TableTMS si présent.

        Args:
            tms_id (int): Identifiant de l'entité TMS.
            id_utilisateur (int): Identifiant de l'utilisateur.
            types_actions (list ou str): Type(s) d'action à annuler (ex: ["valide", "refuse"] ou "passe")

        Returns:
            tuple: (success: bool, message: str, tms_id: int)
        """
        # Normaliser le paramètre types_actions en liste
        if isinstance(types_actions, str):
            types_actions = [types_actions]
        
        # Vérifier que la liste n'est pas vide
        if not types_actions:
            return False, "Aucun type d'action spécifié", None
        
        # Récupérer les relations TMS
        relations = db.session.query(RelationsTMSCandidats).filter_by(tms_id=tms_id).all()
        if not relations:
            return False, f"Aucune relation trouvée pour l'entité TMS {tms_id}", None

        # Récupérer les IDs des matches
        id_matches = [relation.id_match for relation in relations]
        
        # Rechercher toutes les actions correspondantes
        actions = db.session.query(Historique).filter(
            Historique.id_match.in_(id_matches),
            Historique.id_utilisateur == id_utilisateur,
            Historique.action.in_(types_actions)
        ).all()

        if not actions:
            types_str = ", ".join(types_actions)
            return False, f"Aucune action de type '{types_str}' trouvée à annuler pour l'entité TMS {tms_id}", tms_id


        try:
            # Compter les actions par type pour le message de retour
            actions_par_type = {}
            for action in actions:
                actions_par_type[action.action] = actions_par_type.get(action.action, 0) + 1

            # Suppression des actions
            for action in actions:
                db.session.delete(action)

            # Suppression du statut de validation s'il existe
            tms_entry = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
            if tms_entry and tms_entry.statut_validation:
                tms_entry.statut_validation = None

            db.session.commit()
            
            # Construire le message de succès
            details = []
            for type_action, count in actions_par_type.items():
                details.append(f"{count} action(s) '{type_action}'")
            
            message = f"Annulation réussie pour l'entité TMS {tms_id} : {', '.join(details)}"
            
            return True, message, tms_id
            
        except Exception as e:
            db.session.rollback()
            return False, f"Erreur lors de l'annulation pour l'entité TMS {tms_id} : {str(e)}", None


class EvenementsTMS(db.Model):
    
    """
    Une classe pour représenter la table app_alignement.evenements_tms.

    Attributs
    ---------
    id_evenement : sqlalchemy.sql.schema.Column
        Identifiant de l'événement (clé primaire).
    tms_id : sqlalchemy.sql.schema.Column
        Référence au TMS concerné (clé étrangère).
    type_evenement : sqlalchemy.sql.schema.Column
        Type de l'événement (naissance, mort, etc.).
    date_evenement : sqlalchemy.sql.schema.Column
        Date de l'événement.
    precision_date : sqlalchemy.sql.schema.Column
        Précision de la date.
    lieu_evenement : sqlalchemy.sql.schema.Column
        Lieu de l'événement.
    """
    __tablename__ = "evenements_tms"

    id_evenement = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    tms_id = db.Column(db.Integer, db.ForeignKey('table_tms.tms_id', ondelete="CASCADE"), nullable=False)
    type_evenement = db.Column(db.String(20), nullable=True)
    date_evenement = db.Column(db.Date, nullable=True)
    precision_date = db.Column(db.Integer, nullable=True)
    lieu_evenement = db.Column(db.Text, nullable=True)

    tms = db.relationship("TableTMS", backref="evenements")

class EvenementsCandidats(db.Model):
    
    """
    Une classe pour représenter la table app_alignement.evenements_candidats.

    Attributs
    ---------
    id_evenement : sqlalchemy.sql.schema.Column
        Identifiant de l'événement (clé primaire).
    qid : sqlalchemy.sql.schema.Column
        Référence au candidat concerné (clé étrangère).
    type_evenement : sqlalchemy.sql.schema.Column
        Type de l'événement (naissance, mort, etc.).
    date_evenement : sqlalchemy.sql.schema.Column
        Date de l'événement.
    precision_date : sqlalchemy.sql.schema.Column
        Précision de la date.
    rang_date : sqlalchemy.sql.schema.Column
        Rang de la date (hiérarchie temporelle).
    """
    __tablename__ = "evenements_candidats"

    id_evenement = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    qid = db.Column(db.String(20), db.ForeignKey('table_candidats.qid'), nullable=True)
    type_evenement = db.Column(db.String(20), nullable=True)
    date_evenement = db.Column(db.Date, nullable=True)
    precision_date = db.Column(db.Integer, nullable=True)
    rang_date = db.Column(db.String(30), nullable=True)

    candidat = db.relationship("TableCandidats", backref="evenements")

