import pandas as pd
from typing import List, Tuple
import Levenshtein
import unicodedata

### Import des fichiers CSV de calcul
# Chemins des fichiers CSV
chemin_csv_table_tms = "table_TMS.csv"
chemin_csv_table_evenement_tms = "Evenements_TMS.csv"
chemin_csv_table_evenement_candidats = r".\filtered_tables\Evenements_Candidats.csv"
chemin_csv_table_lieux_candidats = r".\filtered_tables\Lieux_Candidats.csv"
chemin_csv_table_relation_tms_candidats = r".\filtered_tables\Relations_TMS_Candidats.csv"
chemin_csv_table_candidats = "table_Candidats.csv"

### Fonctions utilitaires
def get_column_case_insensitive(df, col_name: str) -> str:
    """
    Récupère une colonne du dataframe sans tenir compte de la casse
    
    Args:
        df: DataFrame pandas
        col_name (str): Nom de la colonne recherchée
        
    Returns:
        str: Nom réel de la colonne dans le dataframe
        
    Raises:
        KeyError: Si la colonne n'est pas trouvée
    """
    for col in df.columns:
        if col.lower() == col_name.lower():
            return col
    raise KeyError(f"Colonne {col_name} introuvable dans le dataframe")

def debug_columns(df, filename):
    """Fonction de debug pour afficher les colonnes d'un DataFrame"""
    print(f"\nColonnes disponibles dans {filename}:")
    for i, col in enumerate(df.columns):
        print(f"  {i}: '{col}' (type: {type(col)})")
    print()

def validate_csv_columns():
    """
    Valide que tous les fichiers CSV ont les colonnes requises
    Affiche les avertissements pour les colonnes manquantes
    """
    required_columns = {
        chemin_csv_table_evenement_tms: ['TMS_ID', 'type_evenement', 'lieu_evenement', 'date_evenement', 'precision_date'],
        chemin_csv_table_evenement_candidats: ['QID', 'type_evenement', 'date_evenement', 'precision_date'],
        chemin_csv_table_lieux_candidats: ['QID', 'type_lieu', 'nom_lieu'],
        chemin_csv_table_relation_tms_candidats: ['TMS_ID', 'QID'],
        chemin_csv_table_candidats: ['QID', 'label']
    }
    
    print("\nValidation des fichiers CSV...")
    for file, cols in required_columns.items():
        try:
            df = pd.read_csv(file, nrows=1)
            # Debug: afficher les colonnes disponibles
            debug_columns(df, file)
            
            missing = [col for col in cols if not any(c.lower() == col.lower() for c in df.columns)]
            if missing:
                print(f"ATTENTION: Fichier {file} - colonnes manquantes: {missing}")
            else:
                print(f"OK: Fichier {file} - toutes les colonnes requises sont présentes")
        except Exception as e:
            print(f"ERREUR: Impossible de lire le fichier {file}: {str(e)}")
    print("Validation terminée\n")

### Fonctions de récupération des données
def recup_dates_evenement(csv_file: str, identifiant_entite: str, nom_colonne_id: str = "QID", type_evenement: str = "naissance") -> List[Tuple[str, str]]:
    try:
        df = pd.read_csv(csv_file)
        df.columns = df.columns.str.strip().str.replace('\ufeff', '')

        id_col = get_column_case_insensitive(df, nom_colonne_id)
        type_col = get_column_case_insensitive(df, 'type_evenement')
        date_col = get_column_case_insensitive(df, 'date_evenement')
        precision_col = get_column_case_insensitive(df, 'precision_date')

        events = df[
            (df[id_col].astype(str) == str(identifiant_entite)) &
            (df[type_col].str.lower() == type_evenement)
        ]

        return [
            (str(row[date_col]) if pd.notna(row[date_col]) else "", str(row[precision_col]) if pd.notna(row[precision_col]) else "")
            for _, row in events.iterrows()
        ]
    except Exception as e:
        print(f"Erreur lors de la récupération des dates ({type_evenement}) pour {identifiant_entite}: {e}")
        return []

def recup_lieux_naissance(csv_file: str, candidate_qid: str) -> List[str]:
    """
    Récupère la liste des lieux de naissance possibles d'un candidat donné.
    
    Args:
        csv_file (str): Chemin vers le fichier CSV des lieux
        candidate_qid (str): QID du candidat recherché
        
    Returns:
        List[str]: Liste des lieux de naissance
    """
    try:
        df = pd.read_csv(csv_file)
        
        try:
            qid_col = get_column_case_insensitive(df, 'QID')
            type_col = get_column_case_insensitive(df, 'type_lieu')
            nom_col = get_column_case_insensitive(df, 'nom_lieu')
        except KeyError as e:
            raise ValueError(f"Colonne manquante: {str(e)}")
        
        birth_places = df[
            (df[qid_col].astype(str) == str(candidate_qid)) &
            (df[type_col].str.lower() == 'naissance')
        ]
        
        lieux = []
        for _, row in birth_places.iterrows():
            lieu = row[nom_col] if pd.notna(row[nom_col]) else ""
            if lieu:
                lieux.append(str(lieu))
        
        # Suppression des doublons en conservant l'ordre
        lieux_uniques = []
        for lieu in lieux:
            if lieu not in lieux_uniques:
                lieux_uniques.append(lieu)
        
        return lieux_uniques
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {csv_file} n'existe pas")
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des lieux de naissance: {e}")
        return []

def recup_lieux_mort(csv_file: str, candidate_qid: str) -> List[str]:
    """Récupère les lieux de mort d'un candidat (même structure que recup_lieux_naissance)"""
    # Implémentation similaire à recup_lieux_naissance mais pour les lieux de type 'mort'
    try:
        df = pd.read_csv(csv_file)
        
        try:
            qid_col = get_column_case_insensitive(df, 'QID')
            type_col = get_column_case_insensitive(df, 'type_lieu')
            nom_col = get_column_case_insensitive(df, 'nom_lieu')
        except KeyError as e:
            raise ValueError(f"Colonne manquante: {str(e)}")
        
        death_places = df[
            (df[qid_col].astype(str) == str(candidate_qid)) &
            (df[type_col].str.lower() == 'mort')
        ]
        
        lieux = []
        for _, row in death_places.iterrows():
            lieu = row[nom_col] if pd.notna(row[nom_col]) else ""
            if lieu:
                lieux.append(str(lieu))
        
        lieux_uniques = []
        for lieu in lieux:
            if lieu not in lieux_uniques:
                lieux_uniques.append(lieu)
        
        return lieux_uniques
        
    except FileNotFoundError:
        print(f"Erreur: Le fichier {csv_file} n'existe pas")
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des lieux de mort: {e}")
        return []

def recup_lieu_naissance_tms(csv_file: str, tms_id: str) -> List[str]:
    """
    Récupère le lieu de naissance d'une entité TMS
    
    Args:
        csv_file (str): Chemin vers le fichier CSV des événements TMS
        tms_id (str): Identifiant TMS de l'entité
        
    Returns:
        List[str]: Liste des lieux de naissance
    """
    try:
        df = pd.read_csv(csv_file)
        
        try:
            tms_col = get_column_case_insensitive(df, 'tms_id')
            type_col = get_column_case_insensitive(df, 'type_evenement')
            lieu_col = get_column_case_insensitive(df, 'lieu_evenement')
        except KeyError as e:
            raise ValueError(f"Colonne manquante: {str(e)}")
        
        df_entite = df[
            (df[tms_col].astype(str) == str(tms_id)) & 
            (df[type_col].str.lower() == 'naissance')
        ]
        
        return df_entite[lieu_col].dropna().astype(str).tolist()
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier {csv_file} n'a pas été trouvé")
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération du lieu de naissance TMS: {str(e)}")

def recup_lieu_mort_tms(csv_file: str, tms_id: str) -> List[str]:
    """Récupère le lieu de mort d'une entité TMS (même structure que recup_lieu_naissance_tms)"""
    try:
        df = pd.read_csv(csv_file)
        
        try:
            tms_col = get_column_case_insensitive(df, 'tms_id')
            type_col = get_column_case_insensitive(df, 'type_evenement')
            lieu_col = get_column_case_insensitive(df, 'lieu_evenement')
        except KeyError as e:
            raise ValueError(f"Colonne manquante: {str(e)}")
        
        df_entite = df[
            (df[tms_col].astype(str) == str(tms_id)) & 
            (df[type_col].str.lower() == 'mort')
        ]
        
        return df_entite[lieu_col].dropna().astype(str).tolist()
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Le fichier {csv_file} n'a pas été trouvé")
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération du lieu de mort TMS: {str(e)}")

### Fonctions de comparaison
def compare_dates_with_precision(date_str: str, precision: str) -> str:
    """Extrait la partie de la date selon la précision donnée"""
    try:
        precision = int(precision) if precision else 11  # Par défaut: précision jour
        
        if not date_str or pd.isna(date_str):
            return ""
            
        # Nettoyer la date (au cas où)
        date_str = str(date_str).strip()
        
        # Si la date est juste une année (ex: "1990")
        if precision == 9 and len(date_str) == 4 and date_str.isdigit():
            return date_str
            
        # Compléter les dates partielles pour la comparaison
        if len(date_str) == 4:  # Que l'année
            date_str += "-01-01"
        elif len(date_str) == 7:  # Année-mois
            date_str += "-01"
            
        if precision == 7:  # siècle
            year = int(date_str[:4])
            century = (year - 1) // 100 + 1
            return str(century)
        elif precision == 8:  # décennie
            return date_str[:3] + "0"
        elif precision == 9:  # année
            return date_str[:4]
        elif precision == 10:  # mois
            return date_str[:7]
        elif precision == 11:  # jour
            return date_str[:10]
        else:
            return date_str
    except (ValueError, TypeError):
        return date_str

# def compare_dates(dates_candidat: List[Tuple[str, str]], dates_tms: List[Tuple[str, str]]) -> int:
#     """
#     Compare les dates et retourne le score de comparaison
    
#     Args:
#         dates_candidat: Liste des dates du candidat
#         dates_tms: Liste des dates TMS
        
#     Returns:
#         int: Score de comparaison (1 si match, -1 si pas de match, 0 si pas de données)
#     """
#     if not dates_candidat or not dates_tms:
#         return 0
    
#     match_found = False
    
#     for date_candidat_str, precision_candidat in dates_candidat:
#         for date_tms_str, precision_tms in dates_tms:
#             if not date_candidat_str or not date_tms_str:
#                 continue
                
#             try:
#                 prec_cand = int(precision_candidat) if precision_candidat else 11
#                 prec_tms = int(precision_tms) if precision_tms else 11
#                 min_precision = min(prec_cand, prec_tms)
#             except (ValueError, TypeError):
#                 min_precision = 11
                
#             date_cand = compare_dates_with_precision(date_candidat_str, min_precision)
#             date_tms = compare_dates_with_precision(date_tms_str, min_precision)
            
#             if date_cand and date_tms and date_cand == date_tms:
#                 match_found = True
#                 break
        
#         if match_found:
#             break
    
#     return 1 if match_found else -1

def compare_dates(dates_candidat: List[Tuple[str, str]], dates_tms: List[Tuple[str, str]]) -> int:
    """Compare les dates et retourne le score de comparaison"""
    if not dates_candidat or not dates_tms:
        return 0
    
    match_found = False
    
    for date_candidat_str, precision_candidat in dates_candidat:
        for date_tms_str, precision_tms in dates_tms:
            if not date_candidat_str or not date_tms_str:
                continue
                
            try:
                prec_cand = int(float(precision_candidat)) if precision_candidat else 11
                prec_tms = int(float(precision_tms)) if precision_tms else 11
                min_precision = min(prec_cand, prec_tms)
            except (ValueError, TypeError):
                min_precision = 11
                
            # Calculate normalized dates for comparison
            date_cand = compare_dates_with_precision(date_candidat_str, min_precision)
            date_tms = compare_dates_with_precision(date_tms_str, min_precision)
            
            if date_cand and date_tms and date_cand == date_tms:
                match_found = True
                break
        
        if match_found:
            break
    
    return 1 if match_found else -1

def normaliser_chaine(s: str) -> str:
    """
    Supprime les accents et met la chaîne en minuscules.
    """
    s = s.strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def compare_lieux(lieux_candidat: List[str], lieux_tms: List[str]) -> int:
    """
    Compare les lieux et retourne un score :
    1 si un lieu TMS est exactement ou partiellement contenu dans un lieu candidat (et inversement),
    -1 si aucune correspondance,
    0 si données manquantes.
    """
    if not lieux_candidat or not lieux_tms:
        return 0

    for lieu_candidat in lieux_candidat:
        lc_norm = normaliser_chaine(lieu_candidat)
        for lieu_tms in lieux_tms:
            lt_norm = normaliser_chaine(lieu_tms)

            if lc_norm == lt_norm:
                return 1
            elif lt_norm in lc_norm or lc_norm in lt_norm:
                return 1

    return -1


def mots_ordonnes_identiques(nom1: str, nom2: str) -> bool:
    mots1 = set(nom1.lower().split())
    mots2 = set(nom2.lower().split())
    return mots1 == mots2

def compare_noms(nom_candidat: str, nom_tms: str, seuil_relatif: float = 0.15) -> int:
    """
    Compare deux noms et retourne un score de similarité.
    
    Args:
        nom_candidat: Nom du candidat
        nom_tms: Nom TMS
        seuil_relatif: Seuil maximal 15% pour la distance relative de Levenshtein

    Returns:
        int: 
            1 si correspondance exacte ou mêmes mots dans un ordre différent,
            0 si la distance de Levenshtein est acceptable (≤ seuil relatif),
            -1 sinon.
    """
    if not nom_candidat or not nom_tms:
        return 0

    # Normalisation
    nom_candidat_norm = nom_candidat.lower().strip()
    nom_tms_norm = nom_tms.lower().strip()

    # Cas 1 : correspondance exacte
    if nom_candidat_norm == nom_tms_norm:
        return 1

    # Cas 2 : mêmes mots, ordre différent
    if mots_ordonnes_identiques(nom_candidat_norm, nom_tms_norm):
        return 1

    # Cas 3 : comparer avec distance de Levenshtein relative
    dist = Levenshtein.distance(nom_candidat_norm, nom_tms_norm)
    max_len = max(len(nom_candidat_norm), len(nom_tms_norm))

    if max_len == 0:
        return 0  # sécurité (devrait être capté plus haut)

    ratio = dist / max_len
    if ratio <= seuil_relatif:
        return 0
    else:
        return -1


### Fonction de recuperation des noms TMS
def recup_nom_tms(table_tms, tms_id: str) -> str:
    """
    Récupère le nom d'une entité TMS à partir de son ID
    
    Args:
        table_tms: DataFrame des entités TMS
        tms_id (str): Identifiant TMS de l'entité
        
    Returns:
        str: Nom de l'entité TMS ou une chaîne vide si non trouvé
    """
    try:
        tms_col = get_column_case_insensitive(table_tms, 'TMS_ID')
        # Essayons différentes variations de noms de colonnes pour le nom
        nom_col = None
        possible_name_cols = ['DisplayName', 'display_name', 'nom', 'name', 'label', 'Label']
        
        for col_name in possible_name_cols:
            try:
                nom_col = get_column_case_insensitive(table_tms, col_name)
                break
            except KeyError:
                continue
        
        if nom_col is None:
            print(f"Aucune colonne de nom trouvée dans table_tms. Colonnes disponibles: {list(table_tms.columns)}")
            return ""
        
        entity = table_tms[table_tms[tms_col].astype(str) == str(tms_id)]
        
        if not entity.empty:
            return str(entity[nom_col].values[0])
        else:
            return ""
    except Exception as e:
        print(f"Erreur lors de la récupération du nom TMS: {e}")
        return ""

### Fonction de recuperation des noms Candidats
def recup_nom_candidat(table_candidats, qid: str) -> str:
    """
    Récupère le nom d'un candidat à partir de son QID
    
    Args:
        table_candidats: DataFrame des candidats
        qid (str): QID du candidat
        
    Returns:
        str: Nom du candidat ou une chaîne vide si non trouvé
    """
    try:
        qid_col = get_column_case_insensitive(table_candidats, 'QID')
        
        # Essayons différentes variations de noms de colonnes pour le nom
        nom_col = None
        possible_name_cols = ['label', 'Label', 'nom', 'name', 'DisplayName', 'display_name']
        
        for col_name in possible_name_cols:
            try:
                nom_col = get_column_case_insensitive(table_candidats, col_name)
                break
            except KeyError:
                continue
        
        if nom_col is None:
            print(f"Aucune colonne de nom trouvée dans table_candidats. Colonnes disponibles: {list(table_candidats.columns)}")
            return ""
        
        entity = table_candidats[table_candidats[qid_col].astype(str) == str(qid)]
        
        if not entity.empty:
            return str(entity[nom_col].values[0])
        else:
            return ""
    except Exception as e:
        print(f"Erreur lors de la récupération du nom du candidat: {e}")
        return ""





### Fonction principale de calcul des flags
def calcul_flag(table_tms, table_evenement_tms, table_candidats, table_evenement_candidats, table_lieux_candidats, table_relation_tms_candidats):
    """
    Calcule le score de correspondance entre entités TMS et candidats
    
    Args:
        table_tms: DataFrame des entités TMS
        table_evenement_tms: DataFrame des événements TMS
        table_evenement_candidats: DataFrame des événements candidats
        table_lieux_candidats: DataFrame des lieux candidats
        table_relation_tms_candidats: DataFrame des relations TMS-Candidats
        
    Returns:
        DataFrame: Table des relations avec les scores mis à jour
    """
    # Colonnes de scores détaillés
    score_columns = [
        "score_flag_date_naissance",
        "score_flag_date_mort", 
        "score_flag_lieu_naissance",
        "score_flag_lieu_mort",
        "score_flag_nom",
        "score_flag"
    ]
    
    # Ajout des colonnes si elles n'existent pas
    for col in score_columns:
        if col not in table_relation_tms_candidats.columns:
            table_relation_tms_candidats[col] = 0
    
    print("\nDébut du calcul des flags...")
    
    for index, row in table_relation_tms_candidats.iterrows():
        try:
            # Récupération des IDs avec gestion de la casse
            id_candidat = row[get_column_case_insensitive(table_relation_tms_candidats, 'QID')]
            id_tms = row[get_column_case_insensitive(table_relation_tms_candidats, 'TMS_ID')]
            
            print(f"Traitement ligne {index}: TMS_ID={id_tms}, QID={id_candidat}")
            
            # Récupération des informations du candidat
            dates_naissance_candidat = recup_dates_evenement(csv_file = chemin_csv_table_evenement_candidats, identifiant_entite = id_candidat, nom_colonne_id = "QID", type_evenement = "naissance")
            dates_mort_candidat = recup_dates_evenement(csv_file = chemin_csv_table_evenement_candidats, identifiant_entite = id_candidat, nom_colonne_id = "QID", type_evenement = "mort")
            lieux_naissance_candidat = recup_lieux_naissance(chemin_csv_table_lieux_candidats, id_candidat)
            lieux_mort_candidat = recup_lieux_mort(chemin_csv_table_lieux_candidats, id_candidat)
            nom_candidat = recup_nom_candidat(table_candidats, id_candidat)
            
            # Récupération des informations TMS
            date_naissance_tms = recup_dates_evenement(csv_file = chemin_csv_table_evenement_tms, identifiant_entite = id_tms, nom_colonne_id = "TMS_ID", type_evenement = "naissance")
            date_mort_tms = recup_dates_evenement(csv_file = chemin_csv_table_evenement_tms, identifiant_entite = id_tms, nom_colonne_id = "TMS_ID", type_evenement = "mort")
            lieu_naissance_tms = recup_lieu_naissance_tms(chemin_csv_table_evenement_tms, id_tms)
            lieu_mort_tms = recup_lieu_mort_tms(chemin_csv_table_evenement_tms, id_tms)
            nom_tms = recup_nom_tms(table_tms, id_tms)
            
            # Calcul des scores individuels
            score_date_naissance = compare_dates(dates_naissance_candidat, date_naissance_tms)
            score_date_mort = compare_dates(dates_mort_candidat, date_mort_tms)
            score_lieu_naissance = compare_lieux(lieux_naissance_candidat, lieu_naissance_tms)
            score_lieu_mort = compare_lieux(lieux_mort_candidat, lieu_mort_tms)
            score_nom = compare_noms(nom_candidat, nom_tms)
            
            # Calcul du score total
            score_total = score_date_naissance + score_date_mort + score_lieu_naissance + score_lieu_mort + score_nom
            
            # Mise à jour des scores dans le DataFrame
            table_relation_tms_candidats.at[index, "score_flag_date_naissance"] = score_date_naissance
            table_relation_tms_candidats.at[index, "score_flag_date_mort"] = score_date_mort
            table_relation_tms_candidats.at[index, "score_flag_lieu_naissance"] = score_lieu_naissance
            table_relation_tms_candidats.at[index, "score_flag_lieu_mort"] = score_lieu_mort
            table_relation_tms_candidats.at[index, "score_flag_nom"] = score_nom
            table_relation_tms_candidats.at[index, "score_flag"] = score_total
            
        except Exception as e:
            print(f"ERREUR ligne {index}: {str(e)}")
            # En cas d'erreur, on met des valeurs d'erreur
            table_relation_tms_candidats.at[index, "score_flag_date_naissance"] = -999
            table_relation_tms_candidats.at[index, "score_flag_date_mort"] = -999
            table_relation_tms_candidats.at[index, "score_flag_lieu_naissance"] = -999
            table_relation_tms_candidats.at[index, "score_flag_lieu_mort"] = -999
            table_relation_tms_candidats.at[index, "score_flag_nom"] = -999
            table_relation_tms_candidats.at[index, "score_flag"] = -999
    
    print("Calcul des flags terminé\n")
    return table_relation_tms_candidats

### Programme principal
if __name__ == "__main__":
    # Validation des fichiers CSV
    validate_csv_columns()
    
    # Chargement des fichiers CSV
    print("Chargement des fichiers CSV...")
    try:
        table_tms = pd.read_csv(chemin_csv_table_tms, sep=",")
        table_evenement_tms = pd.read_csv(chemin_csv_table_evenement_tms, sep=",")
        table_candidats = pd.read_csv(chemin_csv_table_candidats, sep=",")
        table_evenement_candidats = pd.read_csv(chemin_csv_table_evenement_candidats, sep=",")
        table_lieux_candidats = pd.read_csv(chemin_csv_table_lieux_candidats, sep=",")
        table_relation_tms_candidats = pd.read_csv(chemin_csv_table_relation_tms_candidats, sep=",")
        print("Chargement terminé avec succès\n")
        
        # Debug: afficher les colonnes de chaque fichier
        print("=== DEBUG: Colonnes des fichiers chargés ===")
        debug_columns(table_tms, "table_TMS.csv")
        debug_columns(table_evenement_tms, "Evenements_TMS.csv")
        debug_columns(table_evenement_candidats, "Evenements_Candidats.csv")
        debug_columns(table_lieux_candidats, "Lieux_Candidats.csv")
        debug_columns(table_relation_tms_candidats, "Relations_TMS_Candidats.csv")
        print("=== FIN DEBUG ===\n")
        
    except Exception as e:
        print(f"ERREUR lors du chargement des fichiers: {str(e)}")
        exit(1)
    
    # Calcul des flags
    table_relation_tms_candidats = calcul_flag(
        table_tms=table_tms,
        table_evenement_tms=table_evenement_tms,
        table_candidats=table_candidats,
        table_evenement_candidats=table_evenement_candidats,
        table_lieux_candidats=table_lieux_candidats,
        table_relation_tms_candidats=table_relation_tms_candidats
    )
    
    # Sauvegarde des résultats
    output_file = "table_relation_tms_candidats_with_flags.csv"
    table_relation_tms_candidats.to_csv(output_file, index=False)
    print(f"Résultats sauvegardés dans {output_file}")

# ### Programme principal
# if __name__ == "__main__":
#     # Validation des fichiers CSV
#     validate_csv_columns()
    
#     # Chargement des fichiers CSV
#     print("Chargement des fichiers CSV...")
#     try:
#         table_tms = pd.read_csv(chemin_csv_table_tms, sep=",")
#         table_evenement_tms = pd.read_csv(chemin_csv_table_evenement_tms, sep=",")
#         table_candidats = pd.read_csv(chemin_csv_table_candidats, sep=",")
#         table_evenement_candidats = pd.read_csv(chemin_csv_table_evenement_candidats, sep=",")
#         table_lieux_candidats = pd.read_csv(chemin_csv_table_lieux_candidats, sep=",")
#         table_relation_tms_candidats = pd.read_csv(chemin_csv_table_relation_tms_candidats, sep=",")
#         print("Chargement terminé avec succès\n")
        
#         # Debug: afficher les colonnes de chaque fichier
#         print("=== DEBUG: Colonnes des fichiers chargés ===")
#         debug_columns(table_tms, "table_TMS.csv")
#         debug_columns(table_evenement_tms, "Evenements_TMS.csv")
#         debug_columns(table_evenement_candidats, "Evenements_Candidats.csv")
#         debug_columns(table_lieux_candidats, "Lieux_Candidats.csv")
#         debug_columns(table_relation_tms_candidats, "Relations_TMS_Candidats.csv")
#         print("=== FIN DEBUG ===\n")
        
#     except Exception as e:
#         print(f"ERREUR lors du chargement des fichiers: {str(e)}")
#         exit(1)
    
#     # Sélectionner une seule entité TMS pour le test
#     tms_id_test = "224274"  # Remplacez par l'ID TMS que vous voulez tester
#     print(f"\n=== TEST sur une seule entité TMS: {tms_id_test} ===")
    
#     # Filtrer la table des relations pour ne garder que cette entité
#     table_relation_test = table_relation_tms_candidats[
#         table_relation_tms_candidats[get_column_case_insensitive(table_relation_tms_candidats, 'TMS_ID')].astype(str) == str(tms_id_test)
#     ].copy()
    
#     if table_relation_test.empty:
#         print(f"Aucune relation trouvée pour TMS_ID={tms_id_test}")
#         exit(1)
    
#     print(f"Nombre de candidats à tester pour cette entité: {len(table_relation_test)}")
    
#     # Calcul des flags uniquement pour cette entité
#     table_relation_test = calcul_flag(
#         table_tms=table_tms,
#         table_evenement_tms=table_evenement_tms,
#         table_candidats=table_candidats,
#         table_evenement_candidats=table_evenement_candidats,
#         table_lieux_candidats=table_lieux_candidats,
#         table_relation_tms_candidats=table_relation_test
#     )
    
#     # Afficher les résultats détaillés pour cette entité
#     print("\n=== Résultats du test ===")
#     print(table_relation_test)
    
#     # Sauvegarde des résultats
#     output_file = f"test_relation_tms_{tms_id_test}_with_flags.csv"
#     table_relation_test.to_csv(output_file, index=False)
#     print(f"\nRésultats du test sauvegardés dans {output_file}")