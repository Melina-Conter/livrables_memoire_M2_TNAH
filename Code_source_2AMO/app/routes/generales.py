
from ..app import app, db, login, csrf
from flask import render_template, request, flash, redirect, url_for, current_app, send_file, session
from ..config import Config
from dotenv import load_dotenv
from ..models.formulaires import AjoutUtilisateur, Connexion, ChangerMdp, Preferences
from ..models.donnees_PRA import Constituent
from ..models.base_principale import TableTMS, TableCandidats, Utilisateurs, RelationsTMSCandidats, LieuxCandidats, Historique, EvenementsTMS, EvenementsCandidats 
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import desc, text
from flask_wtf.csrf import CSRFProtect
import json

@app.route("/")
def accueil():
    """
    Affiche la page d'accueil de l'application.
    Cette fonction est appelée lorsque l'utilisateur accède à la racine de l'application.

    Returns
    -------
        str: Le contenu HTML de la page d'accueil.
    """
    return render_template("pages/accueil.html")

@app.route("/inscription", methods=['GET', 'POST'])
def ajout_utilisateur():
    """
    Gère l'ajout d'un nouvel utilisateur via un formulaire.
    Cette fonction traite les données soumises par un formulaire d'inscription.
    Si les données sont valides, un nouvel utilisateur est ajouté à la base de données.
    En cas de succès, l'utilisateur est redirigé vers la page d'accueil.
    Sinon, les erreurs sont affichées à l'utilisateur.
    Returns
    -------
        - Une redirection vers la page d'accueil si l'ajout est réussi.
        - Le rendu du formulaire d'inscription avec des messages d'erreur en cas d'échec.
    """
    form = AjoutUtilisateur()
    if form.validate_on_submit():
        print("Validation réussie")
        try:
            statut, donnees = Utilisateurs.ajout(
                email=request.form.get("email", None),
                password=request.form.get("password", None)
            )
            if statut is True:
                utilisateur = Utilisateurs.query.filter_by(email=request.form.get("email")).first()
                if utilisateur:
                    login_user(utilisateur)
                    print(f"Utilisateur connecté: {current_user.is_authenticated}")
                    flash("Inscription réussie, vous êtes maintenant connecté.e.", "success")
                    return redirect(url_for("accueil"))
                else:
                    flash("Erreur lors de la connexion automatique.", "warning")
            else:
                for erreur in donnees:
                    flash(erreur, "danger")
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'inscription : {e}")
            flash("Une erreur inattendue s'est produite lors de l'inscription.", "danger")
    
    return render_template("partials/formulaires/inscription.html", form=form)

#Connexion et gestion des erreurs lors de la connexion
@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    """ Gère la connexion d'un utilisateur.
    Cette fonction vérifie si l'utilisateur est déjà authentifié. Si oui, il est redirigé vers la page "accueil".
    Sinon, elle traite les données soumises via un formulaire de connexion, effectue des vérifications sur l'email, 
    le pseudo et le mot de passe, et connecte l'utilisateur si les informations sont valides.
    
    Returns
    ------
        - Redirige vers la page "accueil" si l'utilisateur est déjà connecté ou après une connexion réussie.
        - Affiche le formulaire de connexion avec des messages d'erreur si les informations fournies sont incorrectes.

    Exceptions gérées
    -----------------
        - Email non reconnu.
        - Mot de passe incorrect."""
    
    form = Connexion()

    if current_user.is_authenticated is True:
        return redirect(url_for("accueil"))

    if form.validate_on_submit():
        email = request.form.get("email", None)
        password = request.form.get("password", None)
    
        """
        Vérifications et gestion des erreurs par étapes : 
            - vérification de l'email
            - vérification du mdp
        quand ce qui a été rentré dans le formulaire ne correspond pas à ce qui est dans la base de données
        """

        utilisateur = Utilisateurs.query.filter_by(email=email).first()

        if not utilisateur:
            flash("Cet email n'est pas reconnu.", "danger")
            return render_template("partials/formulaires/connexion.html", form=form, email=email, password=password)

        if not check_password_hash(utilisateur.mdp, password):
            flash("Ce mot de passe n'est pas reconnu.", "danger")
            return render_template("partials/formulaires/connexion.html", form=form, email=email, password=password)

        login_user(utilisateur)
        session.permanent = True
        return redirect(url_for("validation"))

    return render_template("partials/formulaires/connexion.html", form=form)

login.login_view='connexion'

#Se déconnecter et être redirigé vers la page d'accueil
@app.route("/deconnexion", methods=["POST","GET"])
def deconnexion():
    """
    Déconnecte l'utilisateur actuel s'il est authentifié.

    Cette fonction vérifie si l'utilisateur actuel est authentifié. 
    Si c'est le cas, elle effectue la déconnexion de l'utilisateur, 
    affiche un message de confirmation, et redirige vers la page d'accueil.

    Retourne
    -------
        werkzeug.wrappers.Response: Une redirection vers la page d'accueil.
    """
    if current_user.is_authenticated is True:
        logout_user()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for("accueil"))

#Deconnexion automatique si fermeture de l'onglet du navigateur
@app.route('/deconnexion_auto', methods=['POST'])
@csrf.exempt # Exempte cette route de la protection CSRF
def deconnexion_auto():
    if current_user.is_authenticated:
        logout_user()
    return '', 204


#Changement de mot de passe
@app.route("/changer-mot-de-passe", methods=["GET", "POST"])
def chgnt_mdp():
    """
    Route pour permettre à un utilisateur de changer son mot de passe
    sans être connecté (par exemple en cas d'oubli). L'utilisateur
    doit fournir une adresse email existante et un nouveau mot de passe.

    Retourne
    --------
        - render_template : Affiche le formulaire de changement de mot de passe (GET).
        - redirect : Redirige vers la page d'accueil avec un message de confirmation (POST).
    """
    form = ChangerMdp()
    
    if form.validate_on_submit():
        utilisateur = Utilisateurs.query.filter_by(email=form.email.data).first()
        
        if not utilisateur:
            flash("Aucun utilisateur n'est associé à cette adresse email.", "danger")
        else:
            utilisateur.mdp = generate_password_hash(form.new_password.data)
            try:
                db.session.commit()
                flash("Votre mot de passe a été changé avec succès !", "success")
                return redirect(url_for("validation"))
            except Exception as e:
                db.session.rollback()
                flash("Une erreur est survenue lors de la mise à jour du mot de passe.", "danger")
    
    return render_template('partials/formulaires/changemdp.html', form=form)


@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    """
    Enregistre les préférences de domaines TMS de l'utilisateur connecté.
    Par défaut, à la création, les utilisateurs ont pour préférence la catégorie "Tous".

    Retourne
    ---------
        - render_template : Affiche le formulaire de choix des préférences (GET).
        - redirect : Redirige vers la page du profil de l'utilisateur avec un message de confirmation (POST).
    """
    ### Recupération des statistiques de traitement par domaines
    requete = text("""
    SELECT
    type_dossier,
    statut_libelle,
    COUNT(DISTINCT tms_id) AS nb_tms_id
    FROM (
    SELECT
        tt.tms_id,
        doc.value AS type_dossier,
        CASE
        WHEN tt.statut_validation IS NULL THEN 'A traiter'
        WHEN tt.statut_validation = 'aligne' THEN 'Aligné'
        WHEN tt.statut_validation = 'non_aligne' THEN 'Non aligné'
        END AS statut_libelle
    FROM app_alignement.table_tms tt,
        jsonb_array_elements_text(tt.dossiers_documentation::jsonb) AS doc
    WHERE tt.dossiers_documentation IS NOT NULL
        AND jsonb_array_length(tt.dossiers_documentation::jsonb) > 0
        AND (tt.statut_validation IS NULL OR tt.statut_validation IN ('aligne', 'non_aligne'))

    UNION ALL

    SELECT
        tt.tms_id,
        'autres' AS type_dossier,
        CASE
        WHEN tt.statut_validation IS NULL THEN 'A traiter'
        WHEN tt.statut_validation = 'aligne' THEN 'Aligné'
        WHEN tt.statut_validation = 'non_aligne' THEN 'Non aligné'
        END AS statut_libelle
    FROM app_alignement.table_tms tt
    WHERE (tt.dossiers_documentation IS NULL
            OR jsonb_array_length(tt.dossiers_documentation::jsonb) = 0)
        AND (tt.statut_validation IS NULL OR tt.statut_validation IN ('aligne', 'non_aligne'))
    ) AS sub
    GROUP BY type_dossier, statut_libelle
    ORDER BY type_dossier, statut_libelle;
    """)

    # Exécution
    result = db.session.execute(requete).mappings()

    # Transformation du résultat en liste de dictionnaires
    stats_domaines = [
        {
            "type_dossier": row["type_dossier"],
            "statut_libelle": row["statut_libelle"],
            "nb_tms_id": row["nb_tms_id"]
        }
        for row in result.fetchall()
    ]
    

    ### Gestion du formulaire de préférences
    form = Preferences()

    if request.method == "GET":
        form.set_preferences_utilisateur(current_user)

    if form.validate_on_submit():
        try:
            print(f"Données du formulaire : {form.domaines_entites_tms.data}")
            # Ici on stocke directement la liste Python, pas json.dumps()
            current_user.preferences = form.domaines_entites_tms.data  
            db.session.commit()
            prefs_str = ", ".join(form.domaines_entites_tms.data)
            flash(f"Préférences mises à jour : {prefs_str}.", "success")
            return redirect(url_for("preferences"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la sauvegarde : {str(e)}", "danger")

    return render_template("pages/preferences.html", form=form, stats_domaines=stats_domaines)

@app.route("/historique")
@login_required
def historique():
    """
    Affiche l'historique des actions de l'utilisateur connecté.
    Returns
    -------
        str: Le contenu HTML de la page d'historique.
    """
    if not current_user.is_authenticated:
        flash("Vous devez être connecté pour accéder à cette page.", "warning")
        return redirect(url_for("accueil"))
    
    per_page = current_app.config.get("ACTIONS_PER_PAGE", 10)  # Valeur par défaut si non définie
    page = request.args.get('page', 1, type=int)
    
    # Récupération de toutes les actions avec jointures
    all_actions = db.session.query(Historique)\
        .join(RelationsTMSCandidats, Historique.id_match == RelationsTMSCandidats.id_match)\
        .join(TableTMS, RelationsTMSCandidats.tms_id == TableTMS.tms_id)\
        .join(TableCandidats, RelationsTMSCandidats.qid == TableCandidats.qid)\
        .filter(Historique.id_utilisateur == current_user.id_utilisateur)\
        .order_by(desc(Historique.date_heure_action))\
        .all()
    
    # Traitement des actions pour les regrouper par TMS et par minute
    actions_groupees = {}
    
    for action in all_actions:
        # Création d'une clé unique basée sur TMS ID et date/heure tronquée à la minute
        date_minute = action.date_heure_action.replace(second=0, microsecond=0)
        cle_action = f"{date_minute.strftime('%Y%m%d_%H%M')}_{action.match.tms_id}"
        
        if cle_action not in actions_groupees:
            # Initialiser l'entrée pour cette clé
            actions_groupees[cle_action] = {
                'cle_action': cle_action,
                'date_heure_obj': date_minute,  # Garder l'objet datetime pour le tri
                'date_heure': date_minute.strftime('%d/%m/%Y %H:%M'),  # Format JJ/MM/AAAA HH:MM
                'tms_id': action.match.tms_id,
                'displayname': action.match.tms.displayname if action.match.tms else 'N/A',
                'candidats_valides': [],
                'nb_candidats_valides': 0,
                'nb_candidats_refuses': 0,
                'nb_candidats_passes': 0,
                'type': None  # Sera défini selon les actions trouvées
            }
        
        # Traitement selon le type d'action
        if action.action == "passe":
            actions_groupees[cle_action]['nb_candidats_passes'] += 1
            actions_groupees[cle_action]['type'] = 'passe'
        elif action.action == "valide":
            # Ajouter le candidat validé
            candidat_info = {
                'qid': action.match.qid,
                'label': action.match.candidat.label if action.match.candidat else 'N/A'
            }
            actions_groupees[cle_action]['candidats_valides'].append(candidat_info)
            actions_groupees[cle_action]['nb_candidats_valides'] += 1
            # Définir le type comme valide_refuse (il peut y avoir des validations et des refus)
            if actions_groupees[cle_action]['type'] != 'valide_refuse':
                actions_groupees[cle_action]['type'] = 'valide_refuse'
        elif action.action == "refuse":
            actions_groupees[cle_action]['nb_candidats_refuses'] += 1
            # Définir le type comme valide_refuse
            if actions_groupees[cle_action]['type'] != 'valide_refuse':
                actions_groupees[cle_action]['type'] = 'valide_refuse'
    
    # Convertir en liste et trier par date décroissante (plus récent en premier)
    actions_list = list(actions_groupees.values())
    actions_list.sort(key=lambda x: x['date_heure_obj'], reverse=True)
    
    # Supprimer la clé date_heure_obj temporaire (utilisée uniquement pour le tri)
    for action in actions_list:
        del action['date_heure_obj']
    
    # Pagination manuelle
    total = len(actions_list)
    start = (page - 1) * per_page
    end = start + per_page
    actions_page = actions_list[start:end]
    
    # Création d'un objet pagination personnalisé
    class CustomPagination:
        def __init__(self, page, per_page, total, items):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = items
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
        
        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            last = self.pages
            for num in range(1, last + 1):
                if num <= left_edge or \
                   (self.page - left_current - 1 < num < self.page + right_current) or \
                   num > last - right_edge:
                    yield num
    
    pagination = CustomPagination(page, per_page, total, actions_page)
    
    # Transmettre les données au format JSON souhaité
    return render_template("pages/historique.html", actions=actions_page, pagination=pagination)


@app.route("/annuler_action/<int:id_tms>/<string:type_action>", methods=["POST"])
@login_required
def annuler_action(id_tms, type_action):
    """
    Annule les actions d'un type donné pour une entité TMS et l'utilisateur courant.
    Args:
        id_tms (int): ID de l'entité TMS concernée.
        type_action (str): Type d'action à annuler (ex: "passe" ou "valide_refuse".)
    Returns:
        Redirect: Vers la page de validation ou historique avec message flash.
    """
    if not current_user.is_authenticated:
        flash("Vous devez être connecté pour effectuer cette action.", "warning")
        return redirect(url_for("accueil"))
   
    # Déterminer les types d'actions à traiter
    if type_action == "valide_refuse":
        types_actions = ["valide", "refuse"]
    else:
        types_actions = [type_action]
   
    # Appeler la méthode modifiée
    success, message, returned_tms_id = Historique.annuler_action(
        tms_id=id_tms,
        id_utilisateur=current_user.id_utilisateur,
        types_actions=types_actions
    )
   
    # Afficher le message et rediriger
    flash(message, "success" if success else "danger")
    
    if success and returned_tms_id:
        return redirect(url_for("validation", tms_id=returned_tms_id))
    else:
        return redirect(url_for("historique"))