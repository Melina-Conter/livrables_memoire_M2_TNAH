import requests
import urllib3
from ..app import app, db, login
from flask import render_template, request, flash, redirect, url_for, current_app, send_file
from ..config import Config
from dotenv import load_dotenv
from ..models.formulaires import AjoutUtilisateur, Connexion, ChangerMdp
from ..models.donnees_PRA import Constituent
from ..models.base_principale import TableTMS, TableCandidats, Utilisateurs, RelationsTMSCandidats, LieuxCandidats, Historique, EvenementsTMS, EvenementsCandidats 
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import cast, String, func, literal, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import select, or_, and_, not_
from sqlalchemy.orm import aliased
import json
from collections import defaultdict

@app.context_processor
def inject_timer_config():
    return {
        'timer_verrou_minutes': app.config['TIMER_INACTIVITE_MINUTES'],
        'timer_deconnexion_auto_minutes': app.config['PERMANENT_SESSION_LIFETIME']
    }


def get_entite_tms():
    """
    Récupère la première entité TMS dont le statut de validation n'est ni "match_communaute", ni "non_aligne", 
    ni "aligne" et n'a pas été passée par l'utilisateur connecté.
    L'entité ne doit pas être verrouillée par un autre utilisateur.
    L'entité doit respecter les préférences de domaines de l'utilisateur.
    Une fois les filtres appliqués, l'entité est choisie en fonction du score_flag des candidats associés,
    en priorisant les entités ayant des candidats avec un score_flag de 5, puis 4, etc., jusqu'à -5.

    Returns
    -------
        TableTMS: L'entité TMS correspondante ou None si aucune entité ne correspond.
    """
    
    now = datetime.now()
    seuil = now - timedelta(minutes=current_app.config['TIMER_INACTIVITE_MINUTES'])

    # Déverrouiller les entités expirées
    db.session.query(TableTMS).filter(
        TableTMS.date_heure_verrouillage < seuil
    ).update({
        'verrouille_par': None,
        'date_heure_verrouillage': None
    })
    db.session.commit()

    # Préférences utilisateur
    user_prefs = current_user.get_preferences() if hasattr(current_user, 'get_preferences') else ['tous']
    if isinstance(user_prefs, str):
        try:
            user_prefs = json.loads(user_prefs)
        except json.JSONDecodeError:
            user_prefs = ['tous']
    filtrer_par_preferences = 'tous' not in user_prefs

    # TMS déjà passés par l'utilisateur
    tms_passes = db.session.query(RelationsTMSCandidats.tms_id).join(
        Historique, RelationsTMSCandidats.id_match == Historique.id_match
    ).filter(
        Historique.id_utilisateur == current_user.id_utilisateur,
        Historique.action == "passe"
    ).distinct()

    # Requête principale avec tous les filtres sauf tri
    query = db.session.query(TableTMS).filter(
        TableTMS.statut_validation.is_(None),
        ~TableTMS.tms_id.in_(tms_passes),
        or_(
            TableTMS.verrouille_par.is_(None),
            TableTMS.date_heure_verrouillage < seuil,
            TableTMS.verrouille_par == current_user.id_utilisateur
        )
    )

    if filtrer_par_preferences and user_prefs:
        conditions = []
        prefs_specifiques = [pref for pref in user_prefs if pref != 'autres']
        if prefs_specifiques:
            conditions.extend([
                TableTMS.dossiers_documentation.contains([pref]) for pref in prefs_specifiques
            ])
        if 'autres' in user_prefs:
            conditions.append(TableTMS.dossiers_documentation.is_(None))
        query = query.filter(or_(*conditions))

    # Récupérer tous les TMS candidats éligibles
    tms_eligibles = query.all()
    if not tms_eligibles:
        return None

    # Obtenir tous les tms_id éligibles
    tms_ids = [tms.tms_id for tms in tms_eligibles]

    # Récupérer tous les candidats associés
    relations = db.session.query(RelationsTMSCandidats).filter(
        RelationsTMSCandidats.tms_id.in_(tms_ids)
    ).all()

    # Grouper les relations par tms_id
    groupes = defaultdict(list)
    for rel in relations:
        groupes[rel.tms_id].append(rel)

    def moyenne_score(tms_id):
        candidats = groupes[tms_id]
        total = sum(c.score_flag for c in candidats if c.score_flag is not None)
        return total / len(candidats)

    # Parcours des priorités de 5 à -5 inclus
    for i in range(5, -6, -1):
        tms_avec_i = [
            tms_id for tms_id, candidats in groupes.items()
            if any(c.score_flag == i for c in candidats)
        ]
        if tms_avec_i:
            meilleur_tms_id = sorted(
                tms_avec_i, key=moyenne_score, reverse=True
            )[0]
            entite = next((tms for tms in tms_eligibles if tms.tms_id == meilleur_tms_id), None)
            if entite:
                entite.verrouille_par = current_user.id_utilisateur
                entite.date_heure_verrouillage = now
                db.session.commit()
                return entite

def get_score_flag_color_class(score_value):
    """
    Retourne la classe CSS Bootstrap correspondant au score_flag.
    
    Args:
        score_value: Valeur du score (-1, 0, ou 1)
        
    Returns:
        str: Classe CSS Bootstrap
    """
    if score_value == 1:
        return 'bg-success'  # Vert
    elif score_value == 0:
        return 'bg-warning'  # Jaune
    elif score_value == -1:
        return 'bg-danger'   # Rouge
    else:
        return 'bg-secondary'  # Gris par défaut

def get_score_flag_display_name(field_name):
    """
    Retourne le nom d'affichage pour un champ de score_flag.
    
    Args:
        field_name (str): Nom du champ
        
    Returns:
        str: Nom formaté pour l'affichage
    """
    display_names = {
        'date_naissance': 'Date naissance',
        'date_mort': 'Date mort',
        'lieu_naissance': 'Lieu naissance',
        'lieu_mort': 'Lieu mort',
        'nom': 'Nom'
    }
    return display_names.get(field_name, field_name.replace('_', ' ').title())

def preprocess_candidat_info(candidat_raw, scores_info=None, type_candidat='Q5'):
    """
    Prétraite les informations d'un candidat issues de la requête SPARQL.
    
    Args:
        candidat_raw (dict): Données brutes du candidat
        scores_info (dict): Informations de scoring depuis RelationsTMSCandidats
        
    Returns:
        dict: Données prétraitées du candidat
    """
    def split_and_clean(value):
        """Divise une chaîne par ';' et nettoie les éléments"""
        if not value:
            return []
        return [item.strip() for item in value.split(';') if item.strip()]
    
    def join_or_default(items, default="Non renseignée"):
        """Joint les éléments avec ' ou ' ou retourne la valeur par défaut"""
        if not items:
            return default
        return ' ou '.join(items)

    def get_match_label(label):
        """
        Vérifie si le label correspond à l'entité TMS actuelle.
        
        Args:
            label (str): Label à vérifier
            
        Returns:
            bool: True si le label correspond, False sinon
        """
        entite_tms = get_entite_tms()
        if entite_tms:
            return label.lower() == entite_tms.displayname.lower()
        return False
    
    # Informations de base
    candidat = {
        'item': candidat_raw.get('item', ''),
        'itemLabel': candidat_raw.get('itemLabel', ''),
        'qid': candidat_raw.get('item', '').replace('http://www.wikidata.org/entity/', '') if candidat_raw.get('item') else '',
        'description': candidat_raw.get('description', ''),
        'description_courte': candidat_raw.get('description', '')[:120] + ('...' if len(candidat_raw.get('description', '')) > 120 else '') if candidat_raw.get('description') else ''
    }
    
    if type_candidat == 'Q5':

        # Dates et lieux de naissance
        dates_naissance = split_and_clean(candidat_raw.get('datesNaissance', ''))
        lieux_naissance = split_and_clean(candidat_raw.get('lieuxNaissance', ''))
        
        
        candidat['naissance'] = {
            'dates': dates_naissance,
            'dates_formatted': join_or_default(dates_naissance),
            'lieux': lieux_naissance,
            'lieux_formatted': join_or_default(lieux_naissance, '') if lieux_naissance else '',
            'has_info': bool(dates_naissance or lieux_naissance)
        }
        
        # Dates et lieux de décès
        dates_mort = split_and_clean(candidat_raw.get('datesMort', ''))
        lieux_mort = split_and_clean(candidat_raw.get('lieuxMort', ''))
        
        candidat['deces'] = {
            'dates': dates_mort,
            'dates_formatted': join_or_default(dates_mort),
            'lieux': lieux_mort,
            'lieux_formatted': join_or_default(lieux_mort, '') if lieux_mort else '',
            'has_info': bool(dates_mort or lieux_mort)
        }
        
        # Genre
        candidat['genre'] = candidat_raw.get('genreLabel', 'Non renseigné')

        # Professions
        occupations = split_and_clean(candidat_raw.get('occupations', ''))
        candidat['occupations'] = {
            'list': occupations,
            'formatted': ', '.join(occupations) if occupations else 'Non renseignée'
        }
        
        # Type pour l'affichage
        candidat['type_affichage'] = type_candidat

        # Relations familiales et professionnelles
        relations = {}
        
        # Père
        if candidat_raw.get('pereLabel'):
            relations['Père'] = [candidat_raw['pereLabel']]
        
        # Mère
        if candidat_raw.get('mereLabel'):
            relations['Mère'] = [candidat_raw['mereLabel']]
        
        # Frères et sœurs
        freres_soeurs = split_and_clean(candidat_raw.get('freresOuSoeurs', ''))
        if freres_soeurs:
            relations['Frères/Sœurs'] = freres_soeurs
        
        # Enfants
        enfants = split_and_clean(candidat_raw.get('enfants', ''))
        if enfants:
            relations['Enfants'] = enfants
        
        # Conjoints
        conjoints = split_and_clean(candidat_raw.get('conjoints', ''))
        if conjoints:
            relations['Conjoints'] = conjoints
        
        # Élèves
        eleves = split_and_clean(candidat_raw.get('eleves', ''))
        if eleves:
            relations['Maître de'] = eleves
        
        # Maîtres
        maitres = split_and_clean(candidat_raw.get('eleveDe', ''))
        if maitres:
            relations['Élève de'] = maitres
        
        candidat['relations'] = {
            'dict': relations,
            'has_relations': bool(relations),
            'formatted': relations  
        }
        
        #dictionnaire des autres labels et s'ils matchent
        candidat['autres_labels'] = []
        for label in split_and_clean(candidat_raw.get('autresLabels', '')):
            candidat['autres_labels'].append((label, get_match_label(label)))
        
        # Ajout des informations de scoring
        if scores_info:
            # Préparation des scores détaillés avec classes CSS
            scores_flag_formatted = {}
            for field_name, score_value in scores_info.get('scores_flag_details', {}).items():
                if score_value is not None:
                    scores_flag_formatted[field_name] = {
                        'value': score_value,
                        'display_name': get_score_flag_display_name(field_name),
                        'css_class': get_score_flag_color_class(score_value)
                    }
            candidat['scores'] = {
                'score_flag': scores_info.get('score_flag'),
                'score_api': scores_info.get('score_api'),
                'score_api_percentage': f"{scores_info.get('score_api', 0):.1f}%" if scores_info.get('score_api') is not None else None,
                'scores_flag_details': scores_info.get('scores_flag_details', {}),
                'scores_flag_formatted': scores_flag_formatted,
                'has_scores': bool(scores_info.get('score_flag') is not None or 
                                scores_info.get('score_api') is not None or 
                                scores_info.get('scores_flag_details'))
            }
        else:
            candidat['scores'] = {
                'score_flag': None,
                'score_api': None,
                'score_api_percentage': None,
                'scores_flag_details': {},
                'scores_flag_formatted': {},
                'has_scores': False
            }

    elif type_candidat != 'Q5':
        dates_fondation = split_and_clean(candidat_raw.get('datesFondation', ''))
        dates_dissolution = split_and_clean(candidat_raw.get('datesDissolution', ''))

        # Type pour l'affichage
        candidat['type_affichage'] = type_candidat

        candidat['fondation'] = {
            'dates': dates_fondation,
            'dates_formatted': join_or_default(dates_fondation),
            'has_info': bool(dates_fondation)
        }
        candidat['dissolution'] = {
            'dates': dates_dissolution,
            'dates_formatted': join_or_default(dates_dissolution),
            'has_info': bool(dates_dissolution)
        }
        candidat['remplace'] = {
            'list': split_and_clean(candidat_raw.get('entitesRemplacees','')),
            'formatted': ', '.join(split_and_clean(candidat_raw.get('entitesRemplacees', ''))) if candidat_raw.get('entitesRemplacees') else 'Non renseigné'
        }
        candidat['remplace_par'] = {
            'list': split_and_clean(candidat_raw.get('remplaceeParx','')),
            'formatted': ', '.join(split_and_clean(candidat_raw.get('remplaceeParx', ''))) if candidat_raw.get('remplaceeParx') else 'Non renseigné'
        }
        candidat['pays'] = {
            'list': split_and_clean(candidat_raw.get('pays', '')),
            'formatted': ', '.join(split_and_clean(candidat_raw.get('pays', ''))) if candidat_raw.get('pays') else 'Non renseigné'
        }
        candidat['sieges'] = {
            'list': split_and_clean(candidat_raw.get('sieges', '')),
            'formatted': ', '.join(split_and_clean(candidat_raw.get('sieges', ''))) if candidat_raw.get('sieges') else 'Non renseigné'
        }
        candidat['types'] = {
            'list': split_and_clean(candidat_raw.get('types', '')),
            'formatted': ', '.join(split_and_clean(candidat_raw.get('types', ''))) if candidat_raw.get('types') else 'Non renseigné'
        }
        candidat['description'] = candidat_raw.get('description', '') or 'Non renseigné'

        #dictionnaire des autres labels et s'ils matchent
        candidat['autres_labels'] = []
        for label in split_and_clean(candidat_raw.get('autresLabels', '')):
            candidat['autres_labels'].append((label, get_match_label(label)))

        # Ajout des informations de scoring
        if scores_info:
             # Préparation des scores détaillés avec classes CSS
            scores_flag_formatted = {}
            for field_name, score_value in scores_info.get('scores_flag_details', {}).items():
                if score_value is not None:
                    scores_flag_formatted[field_name] = {
                        'value': score_value,
                        'display_name': get_score_flag_display_name(field_name),
                        'css_class': get_score_flag_color_class(score_value)
                    }
            candidat['scores'] = {
                'score_flag': scores_info.get('score_flag'),
                'score_api': scores_info.get('score_api'),
                'score_api_percentage': f"{scores_info.get('score_api', 0):.1f}%" if scores_info.get('score_api') is not None else None,
                'scores_flag_details': scores_info.get('scores_flag_details', {}),
                'scores_flag_formatted': scores_flag_formatted,
                'has_scores': bool(scores_info.get('score_flag') is not None or 
                                scores_info.get('score_api') is not None or 
                                scores_info.get('scores_flag_details'))
            }
        else:
            candidat['scores'] = {
                'score_flag': None,
                'score_api': None,
                'score_api_percentage': None,
                'scores_flag_details': {},
                'scores_flag_formatted': {},
                'has_scores': False
            }
    
    return candidat

@app.route("/validation")
@login_required
def validation():
    """
    Affiche la page de validation avec les données d'un constituant spécifique
    et les informations des candidats associés.

    Returns
    -------
        str: Le contenu HTML de la page de validation avec les données injectées.
    """

    # Récupération du constituant
    # Récupération du tms_id dans l'URL si présent
    tms_id_param = request.args.get("tms_id", type=int)

    # Utiliser le tms_id donné, sinon celui déterminé automatiquement
    if tms_id_param:
        id_tms_affichage = tms_id_param
    else:
        infos_entite_tms_affichage = get_entite_tms()
        id_tms_affichage = infos_entite_tms_affichage.tms_id if infos_entite_tms_affichage else None

    constituant = db.session.query(Constituent).filter_by(constituentid=id_tms_affichage).first()
    
    # Récupération des relations TMS ↔ Candidats
    relations = db.session.query(RelationsTMSCandidats).filter_by(tms_id=id_tms_affichage).all()

    # Récupération des candidats liés avec leurs dates et création d'un mapping des scores
    infos_candidats = []
    qids_q5 = []  # QIDs pour les candidats de type Q5 (personnes)
    qids_autres = []  # QIDs pour les autres types de candidats
    scores_mapping = {}  # Mapping QID -> scores de la relation

    # Données du constituant
    donnees = {}
    if constituant:
        donnees = {
            "tms_id": id_tms_affichage,
            "displayname": constituant.displayname,
            "autres_labels": constituant.autres_labels,
            "date_naissance": constituant.date_naissance,
            "date_naissance_historique": constituant.date_naissance_historique,
            "commune_naissance": constituant.commune_naissance,
            "departement_naissance": constituant.departement_naissance,
            "pays_naissance": constituant.pays_naissance,
            "date_mort": constituant.date_mort,
            "date_mort_historique": constituant.date_mort_historique,
            "commune_mort": constituant.commune_mort,
            "departement_mort": constituant.departement_mort,
            "pays_mort": constituant.pays_mort,
            "biographie": constituant.biographie,
            "roles": constituant.roles_creation,
            "periodes_lieux_activites": constituant.activites,
            "domaines_activite": constituant.dossiers_documentation
        }
    
    for relation in relations:
        candidats = db.session.query(TableCandidats).filter_by(qid=relation.qid).all()
        for candidat in candidats:
            # Séparation des QIDs selon le type
            if candidat.type_candidat == 'Q5':
                qids_q5.append(candidat.qid)
            else:
                qids_autres.append(candidat.qid)
            
            # Récupération de tous les scores de la relation
            scores_mapping[candidat.qid] = {
                'score_flag': relation.score_flag,
                'score_api': relation.score_api,
                'scores_flag_details': {}
            }
            
            # Récupération des colonnes score_flag_* spécifiques
            score_flag_columns = [
                'score_flag_date_naissance',
                'score_flag_date_mort', 
                'score_flag_lieu_naissance',
                'score_flag_lieu_mort',
                'score_flag_nom'
            ]
            
            for column_name in score_flag_columns:
                if hasattr(relation, column_name):
                    score_value = getattr(relation, column_name, None)
                    field_name = column_name.replace('score_flag_', '')
                    scores_mapping[candidat.qid]['scores_flag_details'][field_name] = score_value

    # Configuration de la session avec gestion SSL
    session = requests.Session()
    session.verify = False
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    HEADERS = {"Accept": "application/sparql-results+json","User-Agent": "2AMO/0.1 (https://www.musee-orsay.fr/; benoit.deshayes@musee-orsay.fr)"}
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

    # Exécution des requêtes SPARQL selon les types
    try:
        # Requête pour les candidats de type Q5 (personnes)
        if qids_q5:
            qid_values_q5 = " ".join(f"wd:{qid}" for qid in qids_q5)
            query_q5 = f"""
            SELECT ?item ?itemLabel
                ?genreLabel
                (GROUP_CONCAT(DISTINCT ?altLabel; separator="; ") AS ?autresLabels)
                (GROUP_CONCAT(DISTINCT ?typeLabel; separator="; ") AS ?types)
                (GROUP_CONCAT(DISTINCT ?naissanceFormatee; separator="; ") AS ?datesNaissance)
                (GROUP_CONCAT(DISTINCT ?mortFormatee; separator="; ") AS ?datesMort)
                (GROUP_CONCAT(DISTINCT ?lieuNaissanceLabel; separator="; ") AS ?lieuxNaissance)
                (GROUP_CONCAT(DISTINCT ?lieuMortLabel; separator="; ") AS ?lieuxMort)
                (GROUP_CONCAT(DISTINCT ?occupationLabel; separator="; ") AS ?occupations)
                (GROUP_CONCAT(DISTINCT ?nationaliteLabel; separator="; ") AS ?nationalites)
                ?pereLabel
                ?mereLabel
                (GROUP_CONCAT(DISTINCT ?frereOuSoeurLabel; separator="; ") AS ?freresOuSoeurs)
                (GROUP_CONCAT(DISTINCT ?enfantLabel; separator="; ") AS ?enfants)
                (GROUP_CONCAT(DISTINCT ?conjointLabel; separator="; ") AS ?conjoints)
                (GROUP_CONCAT(DISTINCT ?elevesLabel; separator="; ") AS ?eleves)
                (GROUP_CONCAT(DISTINCT ?eleveDeLabel; separator="; ") AS ?eleveDe)
                ?description
            WHERE {{
            VALUES ?item {{ {qid_values_q5} }}
            OPTIONAL {{
                ?item wdt:P21 ?genre.
                ?genre rdfs:label ?genreLabel.
                FILTER(LANG(?genreLabel) = "fr")
            }}
            OPTIONAL {{
                ?item skos:altLabel ?altLabel.
                FILTER(LANG(?altLabel) = "fr")
            }}
            OPTIONAL {{
                ?item wdt:P31 ?type.
            }}
            OPTIONAL {{
                ?item p:P569 ?naissanceStatement.
                ?naissanceStatement psv:P569 ?naissanceNode.
                ?naissanceNode wikibase:timeValue ?dateNaissance.
                ?naissanceNode wikibase:timePrecision ?precisionNaissance.
                BIND(STR(?dateNaissance) AS ?naissanceStr)
                BIND(
                IF(?precisionNaissance = 11,
                    CONCAT(SUBSTR(?naissanceStr, 9, 2), "/", SUBSTR(?naissanceStr, 6, 2), "/", SUBSTR(?naissanceStr, 1, 4)),
                IF(?precisionNaissance = 10,
                    CONCAT(SUBSTR(?naissanceStr, 6, 2), "/", SUBSTR(?naissanceStr, 1, 4)),
                IF(?precisionNaissance = 9,
                    SUBSTR(?naissanceStr, 1, 4),
                    "[date imprécise]"))) AS ?naissanceFormatee)
            }}
            OPTIONAL {{
                ?item p:P570 ?mortStatement.
                ?mortStatement psv:P570 ?mortNode.
                ?mortNode wikibase:timeValue ?dateMort.
                ?mortNode wikibase:timePrecision ?precisionMort.
                BIND(STR(?dateMort) AS ?mortStr)
                BIND(
                IF(?precisionMort = 11,
                    CONCAT(SUBSTR(?mortStr, 9, 2), "/", SUBSTR(?mortStr, 6, 2), "/", SUBSTR(?mortStr, 1, 4)),
                IF(?precisionMort = 10,
                    CONCAT(SUBSTR(?mortStr, 6, 2), "/", SUBSTR(?mortStr, 1, 4)),
                IF(?precisionMort = 9,
                    SUBSTR(?mortStr, 1, 4),
                    "[date imprécise]"))) AS ?mortFormatee)
            }}
            OPTIONAL {{
                ?item wdt:P19 ?lieuNaissance.
            }}
            OPTIONAL {{
                ?item wdt:P20 ?lieuMort.          
                }}
            OPTIONAL {{
                ?item wdt:P106 ?occupation.
                ?occupation rdfs:label ?occupationLabel.
                FILTER(LANG(?occupationLabel) = "fr")
            }}
            OPTIONAL {{
                ?item wdt:P27 ?nationalite.
                ?nationalite rdfs:label ?nationaliteLabel.
                FILTER(LANG(?nationaliteLabel) = "fr")
            }}
            OPTIONAL {{
                ?item wdt:P22 ?pere.
            }}
            OPTIONAL {{
                ?item wdt:P25 ?mere.
            }}
            OPTIONAL {{
                ?item wdt:P3373 ?frereOuSoeur.
            }}
            OPTIONAL {{
                ?item wdt:P40 ?enfant.
            }}
            OPTIONAL {{
                ?item wdt:P26 ?conjoint.
            }}
            OPTIONAL {{
                ?item wdt:P802 ?eleves.
            }}
            OPTIONAL {{
                ?item wdt:P1066 ?eleveDe.
            }}
            OPTIONAL {{
                ?item schema:description ?description.
                FILTER(LANG(?description) = "fr")
            }}
            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "fr,mul,en".
                ?type rdfs:label ?typeLabel.
                ?lieuNaissance rdfs:label ?lieuNaissanceLabel.
                ?lieuMort rdfs:label ?lieuMortLabel.
                ?pere rdfs:label ?pereLabel.
                ?mere rdfs:label ?mereLabel.
                ?frereOuSoeur rdfs:label ?frereOuSoeurLabel.
                ?enfant rdfs:label ?enfantLabel.
                ?conjoint rdfs:label ?conjointLabel.
                ?eleves rdfs:label ?elevesLabel.
                ?eleveDe rdfs:label ?eleveDeLabel.
                ?item rdfs:label ?itemLabel.
            }}
            }}
            GROUP BY ?item ?itemLabel ?genreLabel ?description ?pereLabel ?mereLabel
            """

            # Exécution de la requête pour les personnes (Q5)
            response_q5 = session.get(
                SPARQL_ENDPOINT,
                params={'query': query_q5},
                headers=HEADERS,
                timeout=30
            )
            
            if response_q5.status_code == 200:
                sparql_data_q5 = response_q5.json()
                # Traitement des résultats SPARQL pour les personnes
                for result in sparql_data_q5.get('results', {}).get('bindings', []):
                    candidat_raw = {}
                    for key, value in result.items():
                        candidat_raw[key] = value.get('value', '')
                    
                    # Prétraitement des données candidat avec les scores
                    qid = candidat_raw.get('item', '').replace('http://www.wikidata.org/entity/', '') if candidat_raw.get('item') else ''
                    scores_info = scores_mapping.get(qid)
                    candidat_processed = preprocess_candidat_info(candidat_raw, scores_info, type_candidat='Q5')
                    infos_candidats.append(candidat_processed)
            else:
                current_app.logger.error(f"Erreur SPARQL Q5: {response_q5.status_code}")

        # Requête pour les candidats d'autres types (organisations, lieux, etc.)
        if qids_autres:
            qid_values_autres = " ".join(f"wd:{qid}" for qid in qids_autres)
            query_autres = f"""
            SELECT ?item ?itemLabel
                (GROUP_CONCAT(DISTINCT ?altLabel; separator="; ") AS ?autresLabels)
                (GROUP_CONCAT(DISTINCT ?typeLabel; separator="; ") AS ?types)
                (GROUP_CONCAT(DISTINCT ?entiteRemplaceeLabel; separator="; ") AS ?entitesRemplacees)
                (GROUP_CONCAT(DISTINCT ?remplaceeParLabel; separator="; ") AS ?remplaceeParx)
                (GROUP_CONCAT(DISTINCT ?paysLabel; separator="; ") AS ?pays)
                (GROUP_CONCAT(DISTINCT ?siegeLabel; separator="; ") AS ?sieges)
                (GROUP_CONCAT(DISTINCT ?fondationFormatee; separator="; ") AS ?datesFondation)
                (GROUP_CONCAT(DISTINCT ?dissolutionFormatee; separator="; ") AS ?datesDissolution)
                ?description
            WHERE {{
            VALUES ?item {{ {qid_values_autres} }}

            OPTIONAL {{
                ?item skos:altLabel ?altLabel.
                FILTER(LANG(?altLabel) = "fr")
            }}

            OPTIONAL {{
                ?item wdt:P31 ?type.
                ?type rdfs:label ?typeLabel.
                FILTER(LANG(?typeLabel) = "fr")
            }}

            OPTIONAL {{
                ?item wdt:P1365 ?entiteRemplacee.
            }}

            OPTIONAL {{
                ?item wdt:P1366 ?remplaceePar.
            }}

            OPTIONAL {{
                ?item wdt:P17 ?pays.
                ?pays rdfs:label ?paysLabel.
                FILTER(LANG(?paysLabel) = "fr")
            }}

            OPTIONAL {{
                ?item wdt:P159 ?siege.
            }}

            OPTIONAL {{
                ?item p:P571 ?fondationStatement.
                ?fondationStatement psv:P571 ?fondationNode.
                ?fondationNode wikibase:timeValue ?dateFondation.
                ?fondationNode wikibase:timePrecision ?precisionFondation.
                BIND(STR(?dateFondation) AS ?fondationStr)
                BIND(
                IF(?precisionFondation = 11,
                    CONCAT(SUBSTR(?fondationStr, 9, 2), "/", SUBSTR(?fondationStr, 6, 2), "/", SUBSTR(?fondationStr, 1, 4)),
                IF(?precisionFondation = 10,
                    CONCAT(SUBSTR(?fondationStr, 6, 2), "/", SUBSTR(?fondationStr, 1, 4)),
                IF(?precisionFondation = 9,
                    SUBSTR(?fondationStr, 1, 4),
                    "[date imprécise]"))) AS ?fondationFormatee)
            }}

            OPTIONAL {{
                ?item p:P576 ?dissolutionStatement.
                ?dissolutionStatement psv:P576 ?dissolutionNode.
                ?dissolutionNode wikibase:timeValue ?dateDissolution.
                ?dissolutionNode wikibase:timePrecision ?precisionDissolution.
                BIND(STR(?dateDissolution) AS ?dissolutionStr)
                BIND(
                IF(?precisionDissolution = 11,
                    CONCAT(SUBSTR(?dissolutionStr, 9, 2), "/", SUBSTR(?dissolutionStr, 6, 2), "/", SUBSTR(?dissolutionStr, 1, 4)),
                IF(?precisionDissolution = 10,
                    CONCAT(SUBSTR(?dissolutionStr, 6, 2), "/", SUBSTR(?dissolutionStr, 1, 4)),
                IF(?precisionDissolution = 9,
                    SUBSTR(?dissolutionStr, 1, 4),
                    "[date imprécise]"))) AS ?dissolutionFormatee)
            }}

            OPTIONAL {{
                ?item schema:description ?description.
                FILTER(LANG(?description) = "fr")
            }}

            SERVICE wikibase:label {{
                bd:serviceParam wikibase:language "fr,mul,en".
                ?item rdfs:label ?itemLabel.
                ?siege rdfs:label ?siegeLabel.
                ?entiteRemplacee rdfs:label ?entiteRemplaceeLabel.
                ?remplaceePar rdfs:label ?remplaceeParLabel.
            }}
            }}
            GROUP BY ?item ?itemLabel ?description
            """

            # Exécution de la requête pour les autres types
            response_autres = session.get(
                SPARQL_ENDPOINT,
                params={'query': query_autres},
                headers=HEADERS,
                timeout=30
            )
            
            if response_autres.status_code == 200:
                sparql_data_autres = response_autres.json()
                # Traitement des résultats SPARQL pour les autres types
                for result in sparql_data_autres.get('results', {}).get('bindings', []):
                    candidat_raw = {}
                    for key, value in result.items():
                        candidat_raw[key] = value.get('value', '')
                    
                    # Prétraitement des données candidat avec les scores
                    qid = candidat_raw.get('item', '').replace('http://www.wikidata.org/entity/', '') if candidat_raw.get('item') else ''
                    scores_info = scores_mapping.get(qid)
                    candidat_processed = preprocess_candidat_info(candidat_raw, scores_info, type_candidat='autres')
                    infos_candidats.append(candidat_processed)
            else:
                current_app.logger.error(f"Erreur SPARQL autres types: {response_autres.status_code}")

        # Tri des candidats par score_api décroissant
        infos_candidats.sort(key=lambda x: x['scores']['score_api'] if x['scores']['score_api'] is not None else -1, reverse=True)
                
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Erreur lors de la requête SPARQL: {str(e)}")
        flash("Erreur lors de la récupération des données depuis Wikidata. Veuillez recharger la page.", "danger")
    except Exception as e:
        current_app.logger.error(f"Erreur inattendue: {str(e)}")

    
    return render_template("pages/validation.html", donnees=donnees, infos_candidats=infos_candidats)

### Route pour passer une entité TMS
@app.route("/validation/passer/<int:tms_id>", methods=["POST"])
@login_required
def passer_entite(tms_id):
    """
    Passe une entité TMS et enregistre l'action dans l'historique.
    
    Args:
        tms_id (int): Identifiant de l'entité TMS à passer
        
    Returns:
        Response: Redirection vers la page de validation avec message flash
    """
    
    # Vérification que l'entité existe
    entite = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
    if not entite:
        flash("Entité introuvable", "danger")
        return redirect(url_for('validation'))
    
    # Enregistrement du passage dans l'historique
    success, message, nb_relations = Historique.enregistrer_passage_entite(
        tms_id=tms_id,
        id_utilisateur=current_user.id_utilisateur
    )
    
    if success:
        flash(f"Entité '{entite.displayname}' passée avec succès. {message}", "success")
    else:
        flash(f"Erreur lors du passage de l'entité : {message}", "danger")
    
    return redirect(url_for('validation'))


@app.route("/validation/valider/<int:tms_id>", methods=["POST"])
@login_required
def valider_candidats(tms_id):
    """
    Valide les candidats sélectionnés pour une entité TMS.
    
    Args:
        tms_id (int): Identifiant de l'entité TMS
        
    Returns:
        Response: Redirection vers la page de validation avec message flash
    """
    # Récupération des candidats sélectionnés depuis le formulaire
    candidats_selectionnes = request.form.getlist('candidats_selectionnes')
    
    # Vérification qu'au moins un candidat a été sélectionné
    if not candidats_selectionnes:
        flash("Aucun candidat sélectionné", "warning")
        return redirect(url_for('validation'))
    
    # Vérification que l'entité TMS existe
    entite = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
    if not entite:
        flash("Entité introuvable", "danger")
        return redirect(url_for('validation'))
    
    # Enregistrement de la validation dans l'historique
    success_validation, message_validation, nb_validations = Historique.enregistrer_validation_candidats(
        tms_id=tms_id,
        qids_selectionnes=candidats_selectionnes,
        id_utilisateur=current_user.id_utilisateur
    )
    
    if not success_validation:
        flash(f"Erreur lors de la validation : {message_validation}", "danger")
        return redirect(url_for('validation'))
    
    # Changement du statut de validation de l'entité TMS vers "aligne"
    success_statut, message_statut = TableTMS.changer_statut_validation(
        tms_id=tms_id,
        nouveau_statut="aligne"
    )
    
    if not success_statut:
        flash(f"Candidats validés mais erreur lors du changement de statut : {message_statut}", "warning")
        return redirect(url_for('validation'))
    
    # Messages de succès
    flash(f"Validation réussie ! {message_validation} Statut de l'entité '{entite.displayname}' changé vers 'aligné'.", "success")
    
    return redirect(url_for('validation'))

@app.route("/validation/refuser-tous-candidats/<int:tms_id>", methods=["POST"])
@login_required
def refuser_tous_candidats(tms_id):
    """
    Refuse tous les candidats pour une entité TMS.
    
    Args:
        tms_id (int): Identifiant de l'entité TMS
        
    Returns:
        Response: Redirection vers la page de validation avec message flash
    """
    # Vérification que l'entité TMS existe
    entite = db.session.query(TableTMS).filter_by(tms_id=tms_id).first()
    if not entite:
        flash("Entité introuvable", "danger")
        return redirect(url_for('validation'))
    
    # Enregistrement du refus dans l'historique
    success_refus, message, nb_refus = Historique.enregistrer_refus_tous_candidats(
        tms_id=tms_id,
        id_utilisateur=current_user.id_utilisateur
    )
    
    if not success_refus:
        flash(f"Erreur lors du refus des candidats : {message}", "danger")

    # Enregistrement du  ouveau statut de l'entité TMS vers "non_aligne"
    success_statut, message_statut = TableTMS.changer_statut_validation(
        tms_id=tms_id,
        nouveau_statut="non_aligne"
    )
    if not success_statut:
        flash(f"Candidats refusés mais erreur lors du changement de statut : {message_statut}", "warning")
        return redirect(url_for('validation'))

    #Message de succès
    flash(f"Tous les candidats pour l'entité '{entite.displayname}' ont été refusés. {message}", "success")
    
    return redirect(url_for('validation'))
