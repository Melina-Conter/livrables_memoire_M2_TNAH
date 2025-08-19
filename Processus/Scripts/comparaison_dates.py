import csv
import ast
import re
from datetime import datetime
from dateutil.parser import parse
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter, defaultdict
import traceback
import logging
import os
import pandas as pd

# Configuration du logging
log_file = "comparaison_dates_errors.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()  # Affichage aussi dans la console
    ]
)
logger = logging.getLogger(__name__)

# Fichiers
fichier_alignement = "alignements_sans_error_complet.csv"
fichier_dates_wikidata = "dates_naissance_mort_extraction_full_dump.csv"
fichier_ecarts = "analyse_ecarts_dates.csv"
fichier_ecarts_sup_100 = "ecarts_sup_100.csv"
fichier_ecarts_inf_100 = "ecarts_inf_100.csv"
fichier_graphique = "distribution_ecarts_rangs.png"
fichier_exclusion = "candidats_exclus.csv"

# Dictionnaire de précision Wikidata (valeurs numériques)
PRECISION_WIKIDATA = {
    6: "millénaire",
    7: "siècle",
    8: "décennie",
    9: "année",
    10: "mois",
    11: "jour"
}


def wikidata_precision_to_level(precision_int):
    """Convertit la précision Wikidata en niveau"""
    try:
        precision_int = int(precision_int)
        if precision_int <= 7:
            return "century" if precision_int == 7 else "millennium"
        elif precision_int == 8:
            return "decade"
        elif precision_int == 9:
            return "year"
        else:
            return "day"
    except Exception as e:
        logger.warning(f"Erreur conversion précision Wikidata '{precision_int}': {e}")
        return "unknown"

def parse_wikidata_date(date_str):
    """Parse une date Wikidata au format spécial"""
    if not date_str:
        return None
    try:
        match = re.match(r"^([+-])(\d+)-(\d{2})-(\d{2})", date_str)
        if not match:
            logger.debug(f"Format de date Wikidata non reconnu: '{date_str}'")
            return None
        sign, year_str, month, day = match.groups()
        year = int(year_str)
        if sign == '-':
            year = -year + 1
        
        # Vérification de la plage d'années supportée par datetime (1-9999)
        if year < 1 or year > 9999:
            logger.debug(f"Année {year} hors de la plage supportée pour '{date_str}' - création d'un objet date personnalisé")
            # Créer un objet date personnalisé pour les calculs
            class CustomDate:
                def __init__(self, year, month, day):
                    self.year = year
                    self.month = month
                    self.day = day
                
                def isoformat(self):
                    return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
            
            # Correction des mois et jours à "00" -> "01"
            month_int = int(month)
            day_int = int(day)
            
            if month_int == 0:
                month_int = 1
                logger.debug(f"Correction mois 00->01 pour date Wikidata '{date_str}'")
            
            if day_int == 0:
                day_int = 1
                logger.debug(f"Correction jour 00->01 pour date Wikidata '{date_str}'")
            
            return CustomDate(year, month_int, day_int)
        
        # Correction des mois et jours à "00" -> "01" pour les dates normales
        month_int = int(month)
        day_int = int(day)
        
        if month_int == 0:
            month_int = 1
            logger.debug(f"Correction mois 00->01 pour date Wikidata '{date_str}'")
        
        if day_int == 0:
            day_int = 1
            logger.debug(f"Correction jour 00->01 pour date Wikidata '{date_str}'")
        
        return datetime(year, month_int, day_int).date()
    except Exception as e:
        logger.warning(f"Erreur parsing date Wikidata '{date_str}': {e}")
        return None

def nettoyage_et_recup_precision_date(date_str):
    """Nettoie une date au format alignement et retourne une date normalisée + précision Wikidata"""
    try:
        if pd.isna(date_str) or not date_str.strip():
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

        # Tentative de parsing par dateutil en dernier recours
        parsed = parse(date_str, dayfirst=True).date()
        return parsed, 11  # On suppose la précision maximale

    except Exception as e:
        logger.warning(f"Erreur dans nettoyage_et_recup_precision_date('{date_str}') : {e}")
        return None, None


def calculate_delta(date_align, date_wiki, prec_align, prec_wiki):
    """Calcule l'écart entre deux dates"""
    try:
        if not prec_align or date_wiki is None or prec_wiki == "unknown":
            return None
        wiki_level = wikidata_precision_to_level(prec_wiki)
        return abs(date_align.year - date_wiki.year)
    except Exception as e:
        logger.error(f"Erreur calcul delta: {e}")
        return None

def load_wikidata_dates():
    """Charge les dates Wikidata avec gestion d'erreur"""
    dates_wikidata = {}
    errors_count = 0
    
    try:
        logger.info(f"Chargement du fichier {fichier_dates_wikidata}")
        with open(fichier_dates_wikidata, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    qid = row["QID"]
                    date = row["date"]
                    type_date = row["type_date"]
                    precision = row.get("precision", "")
                    rank = row.get("rang", "")

                    if qid not in dates_wikidata:
                        dates_wikidata[qid] = {
                            "birth": [], "death": [],
                            "birth_precision": [], "death_precision": [],
                            "birth_rank": [], "death_rank": []
                        }

                    if date:
                        d = parse_wikidata_date(date)
                        if d:
                            if type_date == "naissance":
                                dates_wikidata[qid]["birth"].append(d)
                                dates_wikidata[qid]["birth_precision"].append(precision)
                                dates_wikidata[qid]["birth_rank"].append(rank)
                            elif type_date == "mort":
                                dates_wikidata[qid]["death"].append(d)
                                dates_wikidata[qid]["death_precision"].append(precision)
                                dates_wikidata[qid]["death_rank"].append(rank)
                        else:
                            errors_count += 1
                            
                except Exception as e:
                    logger.error(f"Erreur ligne {row_num} du fichier Wikidata: {e}")
                    errors_count += 1
                    
        logger.info(f"Fichier Wikidata chargé: {len(dates_wikidata)} QIDs, {errors_count} erreurs")
        return dates_wikidata
        
    except FileNotFoundError:
        logger.error(f"Fichier {fichier_dates_wikidata} non trouvé")
        raise
    except Exception as e:
        logger.error(f"Erreur critique lors du chargement Wikidata: {e}")
        raise

def process_alignments(dates_wikidata):
    """Traite les alignements avec gestion d'erreur"""
    results = []
    ecarts_annees = []
    errors_count = 0
    processed_count = 0
    used_entities = set()  # Stocke les IDs des entités utilisées
    entities_with_dates = 0  # Compte les entités avec dates valides

    try:
        logger.info(f"Traitement du fichier {fichier_alignement}")
        with open(fichier_alignement, newline='', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            total = len(reader)
            logger.info(f"Nombre total de lignes à traiter: {total}")

            for idx, row in enumerate(reader):
                try:
                    id_alignement = row.get("ConstituentID", f"ligne_{idx}")
                    candidats_raw = row.get("candidats_scores_wikidata", "")
                    date_naissance = row.get("date_naissance", "").strip()
                    date_mort = row.get("date_mort", "").strip()

                    if (idx + 1) % 1000 == 0:
                        logger.info(f"Progression: {(idx+1)/total*100:.1f}% ({idx+1}/{total})")
                    print(f"Progression: {(idx+1)/total*100:.1f}%", end='\r')

                    # Vérifier si l'entité a au moins une date valide
                    has_valid_date = False
                    for date_str in [date_naissance, date_mort]:
                        if date_str:
                            date_align, align_prec = nettoyage_et_recup_precision_date(date_str)
                            if date_align is not None:
                                has_valid_date = True
                                break

                    if has_valid_date:
                        entities_with_dates += 1

                    if not candidats_raw or "Q" not in candidats_raw:
                        continue

                    try:
                        match = re.search(r"\[\((.*?)\)\]", candidats_raw)
                        if not match:
                            continue
                        tuple_str = "[(" + match.group(1) + ")]"
                        candidats = ast.literal_eval(tuple_str)
                    except Exception as e:
                        logger.warning(f"Erreur parsing candidats ligne {idx}: {e}")
                        errors_count += 1
                        continue

                    entity_used = False  # Indique si l'entité a été utilisée pour au moins une comparaison

                    for qid, _ in candidats:
                        if qid not in dates_wikidata:
                            continue

                        for type_date, date_str in [("birth", date_naissance), ("death", date_mort)]:
                            if not date_str.strip():
                                continue

                            try:
                                date_align, align_prec = nettoyage_et_recup_precision_date(date_str)
                                if date_align is None or align_prec is None:
                                    continue

                            except Exception as e:
                                logger.warning(f"Erreur parsing date alignement '{date_str}' ligne {idx}: {e}")
                                errors_count += 1
                                continue

                            dates_list = dates_wikidata[qid][type_date]
                            prec_list = dates_wikidata[qid][f"{type_date}_precision"]
                            rank_list = dates_wikidata[qid][f"{type_date}_rank"]

                            for date_wiki, wiki_prec, rank in zip(dates_list, prec_list, rank_list):
                                try:
                                    delta = calculate_delta(date_align, date_wiki, align_prec, wiki_prec)
                                    if delta is not None:
                                        wiki_prec_str = PRECISION_WIKIDATA.get(int(wiki_prec), "inconnue")
                                        results.append([
                                            id_alignement, qid, rank,
                                            "naissance" if type_date == "birth" else "mort",
                                            date_str, date_wiki.isoformat(),
                                            align_prec, wiki_prec_str, delta
                                        ])
                                        ecarts_annees.append(delta)
                                        processed_count += 1
                                        entity_used = True
                                except Exception as e:
                                    logger.warning(f"Erreur calcul delta ligne {idx}, QID {qid}: {e}")
                                    errors_count += 1

                    if entity_used:
                        used_entities.add(id_alignement)

                except Exception as e:
                    logger.error(f"Erreur traitement ligne {idx}: {e}")
                    errors_count += 1

        logger.info(f"Traitement terminé: {processed_count} comparaisons, {errors_count} erreurs")
        logger.info(f"Entités avec dates valides: {entities_with_dates}/{total}")
        logger.info(f"Entités utilisées pour comparaison: {len(used_entities)}/{total}")
        return results, ecarts_annees, entities_with_dates, len(used_entities), total

    except FileNotFoundError:
        logger.error(f"Fichier {fichier_alignement} non trouvé")
        raise
    except Exception as e:
        logger.error(f"Erreur critique lors du traitement: {e}")
        raise

def create_visualization(results, ecarts_annees):
    """Crée la visualisation avec gestion d'erreur"""
    try:
        logger.info("Création du graphique")
        
        bins = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, float('inf')]
        labels = ["0-1", "1-2", "2-5", "5-10", "10-20", "20-50", "50-100", "100-200", "200-500", "500-1000", "1000+"]

        # Comptage des écarts par tranche
        counts, _ = np.histogram(ecarts_annees, bins=bins)

        # Comptage des rangs par tranche
        rang_par_tranche = defaultdict(list)
        for result in results:
            _, _, rang, _, _, _, _, _, ecart = result
            for i in range(len(bins) - 1):
                if ecart < bins[i + 1]:
                    tranche_label = labels[i]
                    rang_par_tranche[tranche_label].append(rang)
                    break

        # Préparation des données pour stacked bar plot
        rang_types = ["normal", "preferred", "deprecated"]
        counts_par_rang = {r: [] for r in rang_types}

        for tranche in labels:
            rangs = rang_par_tranche.get(tranche, [])
            compteur = Counter(rangs)
            for r in rang_types:
                counts_par_rang[r].append(compteur.get(r, 0))

        # Tracé du graphique
        plt.figure(figsize=(14, 7))
        bottom = np.zeros(len(labels))
        colors = {'normal': 'skyblue', 'preferred': 'orange', 'deprecated': 'green'}

        for r in rang_types:
            plt.bar(labels, counts_par_rang[r], bottom=bottom, label=r, color=colors[r])
            bottom += np.array(counts_par_rang[r])

        plt.xlabel('Écart en années')
        plt.ylabel('Nombre de comparaisons')
        plt.title('Distribution des écarts de dates (en années) par rang')
        plt.xticks(rotation=45)
        plt.legend(title="Rang")

        plt.tight_layout()
        plt.savefig(fichier_graphique)
        plt.close()
        
        logger.info(f"Graphique sauvegardé: {fichier_graphique}")
        return rang_par_tranche
        
    except Exception as e:
        logger.error(f"Erreur création graphique: {e}")
        logger.error(traceback.format_exc())
        raise

def export_results(results):
    """Exporte les résultats avec gestion d'erreur"""
    try:
        # Export des résultats complets
        logger.info(f"Export des résultats vers {fichier_ecarts}")
        with open(fichier_ecarts, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID_alignement", "QID", "Rang", "Type_date",
                "Date_alignement", "Date_wikidata",
                "Precision_align", "Precision_wikidata", "Ecart_annees"
            ])
            writer.writerows(results)

        # Export des écarts > 100 ans
        ecarts_sup_100_count = 0
        logger.info(f"Export des écarts > 100 ans vers {fichier_ecarts_sup_100}")
        with open(fichier_ecarts_sup_100, 'w', newline='', encoding='utf-8') as f_sup:
            writer_sup = csv.writer(f_sup)
            writer_sup.writerow([
                "ID_alignement", "QID", "Rang", "Type_date",
                "Date_alignement", "Date_wikidata",
                "Precision_align", "Precision_wikidata", "Ecart_annees"
            ])
            for row in results:
                if row[-1] > 100:
                    writer_sup.writerow(row)
                    ecarts_sup_100_count += 1

        # Export des écarts ≤ 100 ans
        ecarts_inf_100_count = 0
        logger.info(f"Export des écarts ≤ 100 ans vers {fichier_ecarts_inf_100}")
        with open(fichier_ecarts_inf_100, 'w', newline='', encoding='utf-8') as f_inf:
            writer_inf = csv.writer(f_inf)
            writer_inf.writerow([
                "ID_alignement", "QID", "Rang", "Type_date",
                "Date_alignement", "Date_wikidata",
                "Precision_align", "Precision_wikidata", "Ecart_annees"
            ])
            for row in results:
                if row[-1] <= 100:
                    writer_inf.writerow(row)
                    ecarts_inf_100_count += 1
                    
        logger.info(f"Export terminé: {len(results)} total, {ecarts_sup_100_count} > 100 ans, {ecarts_inf_100_count} ≤ 100 ans")
        return ecarts_inf_100_count > 0
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export: {e}")
        logger.error(traceback.format_exc())
        raise

def construction_csv_exclusion():
    """Construit le fichier CSV des QIDs exclus"""
    try:
        logger.info("Construction du fichier CSV des exclusions")
        
        # Chargement avec pandas pour une approche plus efficace
        df_extraction = pd.read_csv(fichier_dates_wikidata, encoding='utf-8')
        
        # Vérification que le fichier des écarts ≤ 100 existe
        if not os.path.exists(fichier_ecarts_inf_100):
            logger.warning(f"Le fichier {fichier_ecarts_inf_100} n'existe pas encore")
            return
        
        df_ecart_inf_100 = pd.read_csv(fichier_ecarts_inf_100, encoding='utf-8')
        df_ecart_sup_100 = pd.read_csv(fichier_ecarts_sup_100, encoding='utf-8')
        
        if df_extraction.empty or df_ecart_inf_100.empty or df_ecart_sup_100.empty:
            logger.warning("Un des fichiers CSV est vide, aucune exclusion possible.")
            return
            
        if "QID" not in df_extraction.columns or "QID" not in df_ecart_inf_100.columns or "QID" not in df_ecart_sup_100.columns:
            logger.error("Les fichiers CSV doivent contenir une colonne 'QID'.")
            return
        
        # Extraction des QIDs uniques
        qids_extraction = set(df_extraction["QID"].unique())
        qids_ecart_inf_100 = set(df_ecart_inf_100["QID"].unique())
        qids_ecart_sup_100 = set(df_ecart_sup_100["QID"].unique())
        qids_exclus = list()
        for qid in qids_extraction:
            if qid in qids_ecart_sup_100 and qid not in qids_ecart_inf_100:
                qids_exclus.append(qid)
                
        
        if not qids_exclus:
            logger.info("Aucun QID exclus trouvé.")
            return
        
        logger.info(f"Nombre de QIDs exclus: {len(qids_exclus)}")
        
        # Sauvegarde du fichier des exclusions
        with open(fichier_exclusion, 'w', newline='', encoding='utf-8') as f_excl:
            writer = csv.writer(f_excl)
            writer.writerow(["QID"])
            for qid in sorted(qids_exclus):  # Tri pour un fichier plus propre
                writer.writerow([qid])
        
        logger.info(f"Liste des QIDs exclus enregistrée dans {fichier_exclusion}")
        return len(qids_exclus)
        
    except Exception as e:
        logger.error(f"Erreur construction CSV exclusion: {e}")
        logger.error(traceback.format_exc())
        return 0

def analyze_exclusions():
    """Analyse les QIDs exclus avec gestion d'erreur"""
    try:
        logger.info("Analyse des QIDs exclus")
        
        # Extraction des QIDs uniques dans dates_naissance_mort_extraction_full_dump.csv
        qids_wikidata = set()
        with open(fichier_dates_wikidata, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row.get("QID")
                if qid:
                    qids_wikidata.add(qid)

        # Extraction des QIDs uniques dans ecarts_inf_100.csv
        qids_inf_100 = set()
        if os.path.exists(fichier_ecarts_inf_100):
            with open(fichier_ecarts_inf_100, newline='', encoding='utf-8') as f_inf:
                reader_inf = csv.DictReader(f_inf)
                for row in reader_inf:
                    qid = row.get("QID")
                    if qid:
                        qids_inf_100.add(qid)

        # QIDs exclus (présents dans wikidata mais absents du lot des écarts ≤ 100 ans)
        qids_exclus = qids_wikidata - qids_inf_100

        logger.info(f"QIDs total Wikidata: {len(qids_wikidata)}")
        logger.info(f"QIDs écarts ≤ 100 ans: {len(qids_inf_100)}")
        logger.info(f"QIDs exclus: {len(qids_exclus)}")
        
        return len(qids_wikidata), len(qids_inf_100), len(qids_exclus)
        
    except Exception as e:
        logger.error(f"Erreur analyse exclusions: {e}")
        logger.error(traceback.format_exc())
        return 0, 0, 0

def main():
    """Fonction principale avec gestion d'erreur globale"""
    try:
        logger.info("=== DÉBUT DU TRAITEMENT ===")
        
        # Chargement des dates Wikidata
        dates_wikidata = load_wikidata_dates()
        
        # Traitement des alignements
        results, ecarts_annees, entities_with_dates, used_entities_count, total_entities = process_alignments(dates_wikidata)
        
        if not results:
            logger.warning("Aucun résultat généré!")
            return
            
        # Création de la visualisation
        rang_par_tranche = create_visualization(results, ecarts_annees)
        
        # Export des résultats
        export_success = export_results(results)
        
        # Construction du fichier CSV des exclusions (NOUVEAU)
        if export_success:
            nb_exclusions = construction_csv_exclusion()
            if nb_exclusions:
                logger.info(f"Fichier des exclusions créé avec {nb_exclusions} QIDs")
        
        # Affichage console des statistiques par tranche
        print("\nRépartition des rangs par tranche d'écart :")
        labels = ["0-1", "1-2", "2-5", "5-10", "10-20", "20-50", "50-100", "100-200", "200-500", "500-1000", "1000+"]
        rang_types = ["normal", "preferred", "deprecated"]
        
        for tranche in labels:
            rangs = rang_par_tranche.get(tranche, [])
            total = len(rangs)
            if total == 0:
                print(f"{tranche} ans : aucun échantillon")
                continue
            compteur = Counter(rangs)
            details = ", ".join(f"{r} = {compteur[r]} ({compteur[r]/total*100:.1f}%)" for r in rang_types if r in compteur)
            print(f"{tranche} ans : {total} → {details}")
        
        # Analyse des exclusions
        if export_success:
            total_wikidata, total_inf_100, total_exclus = analyze_exclusions()
            print(f"\nNombre total de QIDs dans {fichier_dates_wikidata} : {total_wikidata}")
            print(f"Nombre de QIDs dans {fichier_ecarts_inf_100} (écarts ≤ 100 ans) : {total_inf_100}")
            print(f"Nombre de QIDs exclus (absents du lot écarts ≤ 100 ans) : {total_exclus}")

        # Affichage des statistiques des entités utilisées
        print("\nStatistiques des entités utilisées :")
        print(f"Nombre total d'entités dans le fichier : {total_entities}")
        print(f"Nombre d'entités avec au moins une date valide : {entities_with_dates} ({entities_with_dates/total_entities*100:.1f}%)")
        print(f"Nombre d'entités utilisées pour comparaison : {used_entities_count} ({used_entities_count/total_entities*100:.1f}%)")
        print(f"Nombre d'entités non utilisées : {total_entities - used_entities_count}")
        
        logger.info("=== TRAITEMENT TERMINÉ AVEC SUCCÈS ===")
        
    except Exception as e:
        logger.error("=== ERREUR CRITIQUE ===")
        logger.error(f"Erreur fatale: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()