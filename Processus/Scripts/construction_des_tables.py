import pandas as pd
import os
import json
import csv
import ast
import re
from datetime import datetime
from dateutil.parser import parse
import logging
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

### Table TMS
# Recuperation ID_TMS
def recuperation_ID_DisplayName_tms(chemin_csv):
    df = pd.read_csv(chemin_csv, encoding='utf-8')
    # Sélectionner ConstituentID et DisplayName, enlever les doublons sur ConstituentID
    IDs_DisplayNames_TMS = df[['ConstituentID', 'DisplayName']].drop_duplicates(subset=['ConstituentID'], keep='first')
    # Renommer la colonne ConstituentID en TMS_ID
    IDs_DisplayNames_TMS = IDs_DisplayNames_TMS.rename(columns={'ConstituentID': 'TMS_ID'})
    return IDs_DisplayNames_TMS

# Recuperation du nombre de liens à la création
def ajout_nb_liens_creation(chemin_csv, df_TMS):
    df_nb_liens_creations = pd.read_csv(chemin_csv, encoding='utf-8')
    
    # Check if the column is named 'ConstituentID' instead of 'TMS_ID'
    if 'ConstituentID' in df_nb_liens_creations.columns and 'TMS_ID' not in df_nb_liens_creations.columns:
        df_nb_liens_creations = df_nb_liens_creations.rename(columns={'ConstituentID': 'TMS_ID'})
    
    # Verify columns before merge
    print("Columns in df_TMS:", df_TMS.columns.tolist())
    print("Columns in df_nb_liens_creations:", df_nb_liens_creations.columns.tolist())
    
    df_table_TMS = pd.merge(df_TMS, df_nb_liens_creations, on='TMS_ID', how='left')
    return df_table_TMS

# Récupération du statut si déjà alignés par la communauté avant le projet d'alignement
def ajout_statut_validation_deja_alignes(chemin_csv, df_TMS):
    # Charger le CSV contenant ConstituentID + QID
    df_deja_alignes = pd.read_csv(chemin_csv, encoding='utf-8')

    # Convertir df_deja_alignes['ConstituentID'] en int pour correspondre à df_TMS
    df_deja_alignes['ConstituentID'] = pd.to_numeric(df_deja_alignes['ConstituentID'], errors='coerce')
    
    # Supprimer les lignes avec des NaN après conversion (si des ConstituentID ne sont pas numériques)
    df_deja_alignes = df_deja_alignes.dropna(subset=['ConstituentID'])
    df_deja_alignes['ConstituentID'] = df_deja_alignes['ConstituentID'].astype(int)
    
    # DEBUG: Vérifier après conversion
    print(f"Après conversion - Type des ConstituentID dans df_deja_alignes: {df_deja_alignes['ConstituentID'].dtype}")
    print(f"Premiers ConstituentID convertis: {df_deja_alignes['ConstituentID'].head().tolist()}")
    
    # Créer un ensemble pour les ConstituentID présents dans le CSV QID
    ids_qid = set(df_deja_alignes['ConstituentID'])
    print(f"Nombre d'IDs uniques dans ids_qid après conversion: {len(ids_qid)}")
    
    # Vérifier s'il y a des correspondances
    correspondances = df_TMS['TMS_ID'].isin(ids_qid)
    print(f"Nombre de correspondances trouvées: {correspondances.sum()}")
    
    # Ajouter une nouvelle colonne avec condition
    df_TMS['statut_validation'] = df_TMS['TMS_ID'].apply(
        lambda x: 'match_communaute' if x in ids_qid else None
    )
    
    # Vérifier le résultat
    nb_match_communaute = (df_TMS['statut_validation'] == 'match_communaute').sum()
    print(f"Nombre de 'match_communaute' dans la colonne finale: {nb_match_communaute}")
    
    return df_TMS


# Création du CSV de la table TMS
def creation_table_TMS(chemin_csv_tms, chemin_csv_nb_liens_creations, chemin_csv_qid):
    # Récupérer les ID TMS (uniques)
    df_TMS = recuperation_ID_DisplayName_tms(chemin_csv_tms)
    print(f"Nombre d'ID TMS uniques après déduplication: {len(df_TMS)}")

    # Ajouter le nombre de liens à la création
    df_TMS = ajout_nb_liens_creation(chemin_csv_nb_liens_creations, df_TMS)
    
    # Ajouter le statut de validation si déjà alignés par la communauté
    df_TMS = ajout_statut_validation_deja_alignes(chemin_csv_qid, df_TMS)
    
    # Enregistrer le DataFrame dans un fichier CSV
    df_TMS.to_csv('table_TMS.csv', index=False, encoding='utf-8')
    print("✅ Table TMS créée avec succès : table_TMS.csv")
    print(f"📊 Nombre total d'entrées uniques : {len(df_TMS)}")
    return df_TMS

# Configuration des chemins pour la table TMS
chemin_csv_tms = 'alignements_sans_error_complet.csv'
chemin_csv_nb_liens_creations = 'nb_roles_par_entites.csv'
chemin_csv_qid = 'all_match_preexistant_wikidata.csv'

# Exécution pour la table TMS
creation_table_TMS(chemin_csv_tms, chemin_csv_nb_liens_creations, chemin_csv_qid)

##### TABLE Evenements_TMS
# Fonction de nettoyage des dates
def nettoyage_et_recup_precision_date(date_str):
    """Nettoie une date au format alignement et retourne une date normalisée + précision Wikidata"""
    try:
        if pd.isna(date_str) or not str(date_str).strip() or str(date_str).strip().lower() in ['nan', 'none', '']:
            return None, None

        date_str = str(date_str).strip()

        # Cas : "AAAA ?" ou "AAAA?"
        match = re.match(r'^(\d{4})\s*\?$', date_str)
        if match:
            annee = int(match.group(1))
            return datetime(annee, 1, 1).date(), 9

        # Cas : "AAAA"
        match = re.match(r'^(\d{4})$', date_str)
        if match:
            annee = int(match.group(1))
            return datetime(annee, 1, 1).date(), 9

        # Cas : "AAAA-MM"
        match = re.match(r'^(\d{4})-(\d{1,2})$', date_str)
        if match:
            annee, mois = int(match.group(1)), int(match.group(2))
            return datetime(annee, mois, 1).date(), 10

        # Cas : "JJ/MM/AAAA"
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
        if match:
            jour, mois, annee = map(int, match.groups())
            return datetime(annee, mois, jour).date(), 11

        # Tentative de parsing automatique
        parsed = parse(date_str, dayfirst=True).date()
        return parsed, 11

    except Exception as e:
        logger.warning(f"Erreur dans nettoyage_et_recup_precision_date('{date_str}') : {e}")
        return None, None

# Fonction de nettoyage des lieux
def nettoyage_lieu(lieu_str):
    """Nettoie une chaîne de lieu"""
    if pd.isna(lieu_str) or not str(lieu_str).strip() or str(lieu_str).strip().lower() in ['nan', 'none', '']:
        return None
    return str(lieu_str).strip()

# Fonction principale
def traitement_evenements_tms(chemin_csv_tms):
    df_tms = pd.read_csv(chemin_csv_tms, encoding='utf-8')

    print(f"Colonnes disponibles dans le CSV: {df_tms.columns.tolist()}")
    print(f"Nombre total de lignes: {len(df_tms)}")

    colonnes_dates = [col for col in df_tms.columns if 'date' in col.lower() and ('naissance' in col.lower() or 'mort' in col.lower())]
    colonnes_lieux = [col for col in df_tms.columns if 'lieu' in col.lower() and ('naissance' in col.lower() or 'mort' in col.lower())]

    print(f"Colonnes de dates trouvées: {colonnes_dates}")
    print(f"Colonnes de lieux trouvées: {colonnes_lieux}")

    # Préparation des DataFrames séparés
    df_dates = pd.DataFrame()
    df_lieux = pd.DataFrame()

    # Traitement des dates si disponibles
    if colonnes_dates:
        for col in colonnes_dates:
            df_tms[col] = df_tms[col].astype(str).str.strip()

        df_dates = pd.melt(
            df_tms,
            id_vars=['ConstituentID'],
            value_vars=colonnes_dates,
            var_name='type_evenement',
            value_name='date_evenement'
        )

        # Application du nettoyage avancé
        df_dates[['date_evenement', 'precision_date']] = df_dates['date_evenement'].apply(
            lambda x: pd.Series(nettoyage_et_recup_precision_date(x))
        )
        df_dates['precision_date'] = df_dates['precision_date'].astype('Int64')

        # Nettoyage des noms d'événements
        df_dates['type_evenement'] = df_dates['type_evenement'].str.lower().str.replace('date_', '', regex=False).str.replace('_', '')

    # Traitement des lieux si disponibles
    if colonnes_lieux:
        for col in colonnes_lieux:
            df_tms[col] = df_tms[col].astype(str).str.strip()

        df_lieux = pd.melt(
            df_tms,
            id_vars=['ConstituentID'],
            value_vars=colonnes_lieux,
            var_name='type_evenement',
            value_name='lieu_evenement'
        )

        # Application du nettoyage des lieux
        df_lieux['lieu_evenement'] = df_lieux['lieu_evenement'].apply(nettoyage_lieu)

        # Nettoyage des noms d'événements
        df_lieux['type_evenement'] = df_lieux['type_evenement'].str.lower().str.replace('lieu_', '', regex=False).str.replace('_', '')

    # Fusion avec conservation de tous les événements
    if len(df_dates) > 0 and len(df_lieux) > 0:
        # Cas 1 : On a dates ET lieux - Fusion complète (outer join)
        df_evenements = pd.merge(
            df_dates,
            df_lieux,
            on=['ConstituentID', 'type_evenement'],
            how='outer'  
        )
        print("Fusion des dates et lieux effectuée")
        
    elif len(df_dates) > 0:
        # Cas 2 : Seulement des dates
        df_evenements = df_dates.copy()
        df_evenements['lieu_evenement'] = None
        print("Seulement des dates disponibles")
        
    elif len(df_lieux) > 0:
        # Cas 3 : Seulement des lieux
        df_evenements = df_lieux.copy()
        df_evenements['date_evenement'] = None
        df_evenements['precision_date'] = None
        print("Seulement des lieux disponibles")
        
    else:
        # Cas 4 : Ni dates ni lieux
        print("ERREUR: Aucune colonne de dates ou de lieux trouvée!")
        return pd.DataFrame()

    # Renommer la colonne avant le filtrage final
    df_evenements = df_evenements.rename(columns={'ConstituentID': 'TMS_ID'})

    # Filtrage final : on garde les lignes qui ont AU MOINS une date OU un lieu
    condition_valide = (
        (df_evenements['date_evenement'].notna()) | 
        (df_evenements['lieu_evenement'].notna())
    )
    df_evenements = df_evenements[condition_valide]

    # Statistiques pour le diagnostic
    nb_avec_date = df_evenements['date_evenement'].notna().sum()
    nb_avec_lieu = df_evenements['lieu_evenement'].notna().sum()
    nb_avec_les_deux = ((df_evenements['date_evenement'].notna()) & 
                        (df_evenements['lieu_evenement'].notna())).sum()
    nb_date_seule = ((df_evenements['date_evenement'].notna()) & 
                     (df_evenements['lieu_evenement'].isna())).sum()
    nb_lieu_seul = ((df_evenements['date_evenement'].isna()) & 
                    (df_evenements['lieu_evenement'].notna())).sum()

    print(f"\n=== STATISTIQUES FINALES ===")
    print(f"DataFrame final Evenements_tms: {len(df_evenements)} lignes")
    print(f"Événements avec date: {nb_avec_date}")
    print(f"Événements avec lieu: {nb_avec_lieu}")
    print(f"Événements avec date ET lieu: {nb_avec_les_deux}")
    print(f"Événements avec date SEULEMENT: {nb_date_seule}")
    print(f"Événements avec lieu SEULEMENT: {nb_lieu_seul}")
    print(f"\nAperçu du DataFrame final:")
    print(df_evenements.head(10))

    return df_evenements

# Création et sauvegarde
def creation_table_evenements_tms(chemin_csv_tms):
    df_evenements_tms = traitement_evenements_tms(chemin_csv_tms)
    df_evenements_tms.to_csv('Evenements_TMS.csv', index=False, encoding='utf-8')
    print("✅ Table Evenements_TMS créée avec succès : Evenements_TMS.csv")
    return df_evenements_tms

# Appel de la fonction principale
chemin_csv_tms = 'alignements_sans_error_complet.csv'
creation_table_evenements_tms(chemin_csv_tms)


##### Table Candidats
def extraire_donnees_candidats(qid, claims, labels):
    resultats = []
    nb_ID_externes = 0
    type_entite = None  # Pour stocker l'ID de P31

    for property_id, claim in claims.items():
        # Gérer le cas où claim est une liste
        if isinstance(claim, list):
            for single_claim in claim:
                mainsnak = single_claim.get('mainsnak')
                if not mainsnak:
                    continue
               
                datavalue = mainsnak.get('datavalue')
                datatype = mainsnak.get('datatype')
                
                if not datatype:
                    continue
           
                # Compter les propriétés avec datatype "external-id"
                if datatype == 'external-id':
                    nb_ID_externes += 1
           
                # Récupérer le type d'entité (P31)
                if property_id == 'P31' and datatype == 'wikibase-item' and datavalue:
                    entity_id = datavalue.get('value', {}).get('id')
                    if entity_id:
                        type_entite = entity_id
                        break  # Prendre seulement le premier type
        else:
            # Cas où claim n'est pas une liste (structure alternative)
            mainsnak = claim.get('mainsnak')
            if not mainsnak:
                continue
               
            datavalue = mainsnak.get('datavalue')
            datatype = mainsnak.get('datatype')
            
            if not datatype:
                continue
       
            # Compter les propriétés avec datatype "external-id"
            if datatype == 'external-id':
                nb_ID_externes += 1
       
            # Récupérer le type d'entité (P31)
            if property_id == 'P31' and datatype == 'wikibase-item' and datavalue:
                entity_id = datavalue.get('value', {}).get('id')
                if entity_id:
                    type_entite = entity_id

    # Gestion des labels : priorité au français, sinon mul, sinon anglais, sinon premier label disponible, sinon None
    label = None
    if labels:
        if 'fr' in labels:
            label = labels['fr'].get('value')
        elif 'mul' in labels:
            label = labels['mul'].get('value')
        elif 'en' in labels:
            label = labels['en'].get('value')
        else:
            # Si aucun des labels prioritaires n'est trouvé, prendre le premier label disponible
            first_label_key = next(iter(labels), None)
            if first_label_key:
                label = labels[first_label_key].get('value')
    
    resultats.append((qid, type_entite, nb_ID_externes, label))
    return resultats

def traiter_dossier(dossier_json, chemin_csv_sortie):
    # Vérifier que le dossier existe
    if not os.path.exists(dossier_json):
        print(f"❌ Erreur: Le dossier '{dossier_json}' n'existe pas.")
        return
    
    fichiers = [f for f in os.listdir(dossier_json) if f.endswith('.json')]
    total = len(fichiers)
    
    if total == 0:
        print(f"❌ Aucun fichier JSON trouvé dans le dossier '{dossier_json}'.")
        return
    
    print(f"📁 Dossier trouvé: {dossier_json}")
    print(f"📄 Traitement de {total} fichiers JSON...")
    
    try:
        with open(chemin_csv_sortie, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # En-têtes selon vos spécifications, label au lieu de label_fr
            writer.writerow(['QID', 'type_candidat', 'nb_id_externes', 'label'])
            
            fichiers_traites = 0
            fichiers_erreur = 0
            
            for i, fichier in enumerate(fichiers, 1):
                chemin_fichier = os.path.join(dossier_json, fichier)
                
                try:
                    with open(chemin_fichier, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Gestion des différentes structures JSON
                    if 'entities' in data and data['entities']:
                        qid = list(data['entities'].keys())[0]
                        claims = data['entities'][qid].get('claims', {})
                        labels = data['entities'][qid].get('labels', {})
                    elif 'claims' in data:
                        qid = data.get('id', f'QID_inconnu_{i}')
                        claims = data.get('claims', {})
                        labels = data.get('labels', {})
                    else:
                        print(f"⚠️ Structure inattendue dans {fichier} - saut du fichier")
                        fichiers_erreur += 1
                        continue
                    
                    # Extraction des données
                    donnees = extraire_donnees_candidats(qid, claims, labels)
                    
                    # Écriture dans le CSV
                    for qid, type_candidat, nb_id_externes, label in donnees:
                        writer.writerow([qid, type_candidat, nb_id_externes, label])
                    
                    fichiers_traites += 1
                    
                    # Affichage du progrès
                    if i % 100 == 0 or i == total:
                        print(f"Progression: {i}/{total} fichiers traités ({fichiers_traites} réussis, {fichiers_erreur} erreurs)")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Erreur JSON dans {fichier}: {e}")
                    fichiers_erreur += 1
                    continue
                except Exception as e:
                    print(f"❌ Erreur avec le fichier {fichier}: {e}")
                    fichiers_erreur += 1
                    continue
        
        print(f"✅ Traitement terminé!")
        print(f"📊 Résumé: {fichiers_traites} fichiers traités avec succès, {fichiers_erreur} erreurs")
        print(f"💾 CSV sauvegardé: {chemin_csv_sortie}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier CSV: {e}")

def filtrer_qid_candidats_exclus(chemin_csv_candidats, chemin_csv_exclusion):
    try:
        # Charger le CSV des candidats
        df_candidats = pd.read_csv(chemin_csv_candidats, encoding='utf-8')
        
        # Vérifier si le fichier d'exclusion existe
        if not os.path.exists(chemin_csv_exclusion):
            print(f"⚠️ Fichier d'exclusion non trouvé: {chemin_csv_exclusion}. Retour du DataFrame original.")
            return df_candidats
        
        # Charger le CSV d'exclusion
        df_exclusion = pd.read_csv(chemin_csv_exclusion, encoding='utf-8')
        
        # Vérifier que la colonne 'QID' existe dans les deux DataFrames
        if 'QID' not in df_candidats.columns or 'QID' not in df_exclusion.columns:
            print("❌ La colonne 'QID' est manquante dans l'un des fichiers.")
            return None
        
        # Filtrer les candidats en excluant ceux présents dans le fichier d'exclusion
        df_filtre = df_candidats[~df_candidats['QID'].isin(df_exclusion['QID'])]
        
        print(f"✅ Filtrage terminé! {len(df_filtre)} candidats restants après exclusion.")
        return df_filtre
    
    except Exception as e:
        print(f"❌ Erreur lors du filtrage des candidats: {e}")
        return None

def creation_table_candidats(dossier_json, chemin_csv_sortie, chemin_csv_exclusion):
    print("🚀 Début de la création de la table Candidats...")
    
    # Construction du csv de la table Candidats
    traiter_dossier(dossier_json, chemin_csv_sortie)
    
    # Vérification que le fichier a été créé
    if os.path.exists(chemin_csv_sortie):
        try:
            df = pd.read_csv(chemin_csv_sortie, encoding='utf-8')
            
            # Deduplicate based on QID
            df_deduplicated = df.drop_duplicates(subset=['QID'], keep='first')
            
            # Save the deduplicated data back to the CSV
            df_deduplicated.to_csv(chemin_csv_sortie, index=False, encoding='utf-8')
            
            print(f"✅ Table Candidats créée avec succès (dédupliquée) : {chemin_csv_sortie}")
            print(f"📈 Nombre total de lignes (après déduplication): {len(df_deduplicated)}")
            print(f"📋 Aperçu des premières lignes:")
            print(df_deduplicated.head())
            
            # Si un fichier d'exclusion est fourni, appliquer le filtrage
            if chemin_csv_exclusion:
                print(f"\n🔄 Application du filtrage avec {chemin_csv_exclusion}...")
                df_filtre = filtrer_qid_candidats_exclus(chemin_csv_sortie, chemin_csv_exclusion)
                if df_filtre is not None:
                    diff = len(df_deduplicated) - len(df_filtre)
                    df_filtre.to_csv('Table_Candidats.csv', index=False, encoding='utf-8')
                    print(f"📋 Aperçu de la table filtrée:")
                    print(df_filtre.head())
                    print(f"📉 Nombre de candidats exclus: {diff}")
                    print(f"Nombre de candidats restants: {len(df_filtre)}")
                    
        except Exception as e:
            print(f"⚠️ Fichier créé mais erreur lors de la lecture: {e}")
    else:
        print(f"❌ Échec de la création du fichier {chemin_csv_sortie}")

# Paramètres d'exécution
dossier_json = ".\json_full_dump_entites"  # chemin vers le dossier JSON
chemin_csv_sortie = "Table_Candidats.csv"
chemin_csv_exclusion = "candidats_exclus.csv"

creation_table_candidats(dossier_json, chemin_csv_sortie, chemin_csv_exclusion)

##### Table Evenements_candidats
def extraction_evenements_candidats(chemin_csv_evenements_candidats):
    # Charger le CSV des événements candidats
    df_evenements = pd.read_csv(chemin_csv_evenements_candidats, encoding='utf-8')
    # Appliquer le filtre
    df_evenements_filtre = filtrer_qid_candidats_exclus(chemin_csv_evenements_candidats, "candidats_exclus.csv")
   
    if df_evenements_filtre is not None:
        # 🔥 Nettoyage des dates : suppression des + ou - initiaux
        df_evenements_filtre["date"] = df_evenements_filtre["date"].astype(str).str.replace(r"^[\+\-]", "", regex=True)
        
        # 🔥 Remplacement des 00 par 01 dans les dates et ajustement de la précision
        # Cas 1: AAAA-00-00 -> AAAA-01-01
        mask_dates_00_00 = df_evenements_filtre["date"].str.match(r"^\d{4}-00-00$")
        df_evenements_filtre.loc[mask_dates_00_00, "date"] = df_evenements_filtre.loc[mask_dates_00_00, "date"].str.replace("-00-00", "-01-01")
        df_evenements_filtre.loc[mask_dates_00_00, "precision"] = 9
        
        # Cas 2: AAAA-00-JJ -> AAAA-01-JJ (mois = 00)
        mask_mois_00 = df_evenements_filtre["date"].str.match(r"^\d{4}-00-\d{2}$")
        df_evenements_filtre.loc[mask_mois_00, "date"] = df_evenements_filtre.loc[mask_mois_00, "date"].str.replace(r"^(\d{4})-00-(\d{2})$", r"\1-01-\2", regex=True)
        df_evenements_filtre.loc[mask_mois_00, "precision"] = 9
        
        # Cas 3: AAAA-MM-00 -> AAAA-MM-01 (jour = 00)
        mask_jour_00 = df_evenements_filtre["date"].str.match(r"^\d{4}-\d{2}-00$")
        df_evenements_filtre.loc[mask_jour_00, "date"] = df_evenements_filtre.loc[mask_jour_00, "date"].str.replace(r"^(\d{4})-(\d{2})-00$", r"\1-\2-01", regex=True)
        df_evenements_filtre.loc[mask_jour_00, "precision"] = 9
        
        # Renommer les colonnes
        df_evenements_filtre.rename(columns={
            "type_date": "type_evenement",
            "date": "date_evenement",
            "precision": "precision_date",
            "rang": "rang_date"
        }, inplace=True)
        # Export
        df_evenements_filtre.to_csv('Evenements_Candidats.csv', index=False, encoding='utf-8')
        print(f"✅ Table Evenements_Candidats filtrée créée avec succès : Evenements_Candidats.csv")
    else:
        print("❌ Échec de la création de la table Evenements_Candidats filtrée.")

# Exécution de l'extraction des événements candidats
chemin_csv_evenements_candidats = "dates_naissance_mort_extraction_full_dump.csv"
extraction_evenements_candidats(chemin_csv_evenements_candidats)

###### Table Lieux_Candidats
def creation_table_lieux_candidats(chemin_csv_lieux_rangs_candidats):
    try:
        # Charger le CSV des lieux et rangs candidats
        df_lieux = pd.read_csv(chemin_csv_lieux_rangs_candidats, encoding='utf-8')

        # Filtrer les candidats en excluant ceux présents dans le fichier d'exclusion
        df_lieux_filtre = filtrer_qid_candidats_exclus(chemin_csv_lieux_rangs_candidats, "candidats_exclus.csv")

        if df_lieux_filtre is not None:
            df_lieux_filtre.rename(columns={
                "rang": "rang_lieu"
            }, inplace=True)
            df_lieux_filtre.to_csv('Lieux_Candidats.csv', index=False, encoding='utf-8')
            print(f"✅ Table Lieux_Candidats créée avec succès : Lieux_Candidats.csv")
        else:
            print("❌ Échec de la création de la table Lieux_Candidats filtrée.")
    
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table Lieux_Candidats: {e}")

# Exécution de la création de la table Lieux_Candidats
chemin_csv_lieux_rangs_candidats = "QID_lieux_rangs.csv"
creation_table_lieux_candidats(chemin_csv_lieux_rangs_candidats)

######## Table Relations_TMS_Candidats
def extractions_donnees_matchs(chemin_csv_openrefine):
    try:
        df_matchs = pd.read_csv(chemin_csv_openrefine, encoding='utf-8')
        lignes_resultat = []

        for entite in df_matchs.itertuples(index=False):
            TMS_ID = entite.ConstituentID
            contenu = entite.candidats_scores_wikidata

            # Ignorer les valeurs nulles ou vides
            if pd.isna(contenu) or contenu.strip() == "":
                continue

            try:
                # Corriger la clé non entre guillemets
                contenu_corrige = re.sub(r'(?<!")\bcandidats\b(?!")', "'candidats'", contenu)

                # Convertir en dictionnaire Python
                donnees = ast.literal_eval(contenu_corrige)

                for qid, score in donnees.get('candidats', []):
                    lignes_resultat.append({
                        'TMS_ID': TMS_ID,
                        'QID': qid,
                        'Score_API': score
                    })

            except Exception as e:
                print(f"[!] Erreur pour ConstituentID {TMS_ID} : {e}")
                continue

        return pd.DataFrame(lignes_resultat)

    except Exception as e:
        print(f"[!] Erreur générale : {e}")
        return None

def creation_table_relations_tms_candidats(chemin_csv_openrefine):
    print("🚀 Début de la création de la table Relations_TMS_Candidats...")
    
    # Extraire les données des matchs
    df_relations = extractions_donnees_matchs(chemin_csv_openrefine)

    if df_relations is not None and not df_relations.empty:
        print(f"📊 {len(df_relations)} relations extraites avant filtrage")
        
        # Créer un fichier temporaire pour le filtrage
        temp_file = "temp_relations.csv"
        df_relations.to_csv(temp_file, index=False, encoding='utf-8')
        
        # Appliquer le filtrage
        df_relations_filtre = filtrer_qid_candidats_exclus(temp_file, "candidats_exclus.csv")
        
        # Supprimer le fichier temporaire
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if df_relations_filtre is not None:
            df_relations_filtre.to_csv('Relations_TMS_Candidats.csv', index=False, encoding='utf-8')
            print("✅ Table Relations_TMS_Candidats créée avec succès : Relations_TMS_Candidats.csv")
            print(f"📊 {len(df_relations_filtre)} relations après filtrage")
            return True
        else:
            print("❌ Échec du filtrage de la table Relations_TMS_Candidats.")
            return False
    else:
        print("❌ Aucune donnée à traiter pour la table Relations_TMS_Candidats.")
        return False

# Exécution de la création de la table Relations_TMS_Candidats
chemin_csv_openrefine = 'alignements_sans_error_complet.csv'
relations_creees = creation_table_relations_tms_candidats(chemin_csv_openrefine)

#### Modification table TMS statut validation pour les Non alignés (sans candidats après OpenRefine)
def statut_non_alignes(chemin_table_tms, chemin_table_relation_tms_candidats):
    # Vérifier que les fichiers existent
    if not os.path.exists(chemin_table_tms):
        print(f"❌ Erreur: Le fichier {chemin_table_tms} n'existe pas.")
        return
    
    if not os.path.exists(chemin_table_relation_tms_candidats):
        print(f"❌ Erreur: Le fichier {chemin_table_relation_tms_candidats} n'existe pas.")
        print("💡 Mise à jour du statut non alignés annulée.")
        return
    
    try:
        df_tms = pd.read_csv(chemin_table_tms, encoding='utf-8')
        df_relations = pd.read_csv(chemin_table_relation_tms_candidats, encoding='utf-8')
        
        # Identifier les TMS_ID qui ont des candidats
        tms_ids_avec_candidats = df_relations['TMS_ID'].unique()
        
        # Compter les entités avant mise à jour
        nb_avant = (df_tms['statut_validation'] == 'non_aligne').sum()
        
        # Mettre à jour le statut pour les TMS_ID qui n'ont pas de candidats
        df_tms['statut_validation'] = df_tms.apply(
            lambda row: 'non_aligne' if row['TMS_ID'] not in tms_ids_avec_candidats and pd.isna(row['statut_validation']) else row['statut_validation'],
            axis=1
        )
        
        # Compter les entités après mise à jour
        nb_apres = (df_tms['statut_validation'] == 'non_aligne').sum()
        
        # Enregistrer la table TMS mise à jour
        df_tms.to_csv(chemin_table_tms, index=False, encoding='utf-8')
        print("✅ Statut des non alignés mis à jour dans la table TMS.")
        print(f"📊 {nb_apres - nb_avant} nouveaux statuts 'non_aligne' ajoutés")
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour des statuts: {e}")

# Exécution de la mise à jour des statuts seulement si les relations ont été créées
if relations_creees:
    chemin_table_tms = "table_TMS.csv"
    chemin_table_relation_tms_candidats = "Relations_TMS_Candidats.csv"
    statut_non_alignes(chemin_table_tms, chemin_table_relation_tms_candidats)
else:
    print("⚠️ Mise à jour des statuts non alignés sautée car la table Relations_TMS_Candidats n'a pas été créée.")

print("\n🎉 Traitement terminé!")

##### Filtrage des candidats sur l'ensemble des tables ayant une fk QID
def filter_csv_by_reference_qid(
    csv_files: List[str], 
    reference_csv: str, 
    output_dir: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, pd.DataFrame]:
    """
    Filtre plusieurs fichiers CSV en gardant seulement les lignes dont le QID 
    existe dans le CSV de référence.
    
    Args:
        csv_files: Liste des chemins vers les 3 fichiers CSV à filtrer
        reference_csv: Chemin vers le fichier CSV de référence
        output_dir: Répertoire de sortie pour sauvegarder les CSV filtrés (optionnel)
        verbose: Si True, affiche des messages détaillés
    
    Returns:
        Dictionnaire contenant les DataFrames filtrés avec les noms de fichiers comme clés
    
    Raises:
        ValueError: Si un CSV n'a pas de colonne contenant "qid"
        FileNotFoundError: Si un fichier CSV n'existe pas
    """
    
    def find_qid_column(df: pd.DataFrame, filename: str) -> str:
        """Trouve la colonne contenant 'qid' (insensible à la casse)"""
        qid_columns = [col for col in df.columns if 'qid' in col.lower()]
        
        if not qid_columns:
            raise ValueError(f"Aucune colonne contenant 'qid' trouvée dans {filename}")
        
        if len(qid_columns) > 1 and verbose:
            print(f"Attention: Plusieurs colonnes QID trouvées dans {filename}: {qid_columns}")
            print(f"Utilisation de la première: {qid_columns[0]}")
        
        return qid_columns[0]
    
    # Charger le CSV de référence
    if verbose:
        print(f"Chargement du CSV de référence: {reference_csv}")
    
    ref_df = pd.read_csv(reference_csv)
    ref_qid_col = find_qid_column(ref_df, reference_csv)
    
    # Obtenir la liste des QID de référence
    reference_qids = set(ref_df[ref_qid_col].dropna().astype(str))
    
    if verbose:
        print(f"Nombre de QID uniques dans la référence: {len(reference_qids)}")
    
    filtered_dataframes = {}
    
    # Traiter chaque fichier CSV
    for csv_file in csv_files:
        if verbose:
            print(f"Traitement de: {csv_file}")
        
        # Charger le CSV
        df = pd.read_csv(csv_file)
        original_count = len(df)
        
        # Trouver la colonne QID
        qid_col = find_qid_column(df, csv_file)
        
        # Filtrer les lignes selon les QID de référence
        df_filtered = df[df[qid_col].astype(str).isin(reference_qids)]
        filtered_count = len(df_filtered)
        
        if verbose:
            print(f"  Lignes avant filtrage: {original_count}")
            print(f"  Lignes après filtrage: {filtered_count}")
            print(f"  Lignes supprimées: {original_count - filtered_count}")
        
        # Stocker le DataFrame filtré
        filename_key = os.path.basename(csv_file)
        filtered_dataframes[filename_key] = df_filtered
        
        # Sauvegarder si un répertoire de sortie est spécifié
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{filename_key}")
            df_filtered.to_csv(output_path, index=False)
            if verbose:
                print(f"  Fichier sauvegardé: {output_path}")
    
    if verbose:
        print(f"Traitement terminé pour {len(csv_files)} fichiers CSV")
    
    return filtered_dataframes

# Execution de la fonction de filtrage
chemin_csv_reference = "Table_Candidats.csv"
chemin_csv_evenements_candidats = "Evenements_Candidats.csv"
chemin_csv_lieux_candidats = "Lieux_Candidats.csv"
chemin_csv_relations_tms_candidats = "Relations_TMS_Candidats.csv"
# Liste des fichiers CSV à filtrer
csv_files = [
    chemin_csv_evenements_candidats,
    chemin_csv_lieux_candidats,
    chemin_csv_relations_tms_candidats
]
# Répertoire de sortie pour les CSV filtrés
output_dir = "filtered_tables"
# Filtrer les CSV
filtered_data = filter_csv_by_reference_qid(
    csv_files=csv_files, 
    reference_csv=chemin_csv_reference, 
    output_dir=output_dir, 
    verbose=True
)

