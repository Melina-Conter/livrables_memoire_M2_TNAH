import csv
import json
import re
import time
import os
import urllib3
import requests
from itertools import islice
from datetime import datetime

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
CSV_PATH = "alignements_sans_error_complet.csv"
CACHE_PATH = "wikidata_sparql_batch_lieux_only_et_rangs.json"
DUMP_DIR = "dumps_sparql_lieux_avec_rangs"
BATCH_SIZE = 50
HEADERS = {"Accept": "application/sparql-results+json"}

def extract_qids_from_csv(csv_path):
    qids = set()
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("candidats_scores_wikidata", "")
            found_qids = re.findall(r"Q\d+", raw)
            qids.update(found_qids)
    return list(qids)

def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

def build_sparql_query(qids):
    qid_values = " ".join(f"wd:{qid}" for qid in qids)
    return f"""
        SELECT ?item ?lieuNaissanceLabel ?rangNaissance ?lieuMortLabel ?rangMort WHERE {{
        VALUES ?item {{ {qid_values} }}
        OPTIONAL {{
            ?item p:P19 ?birthPlaceStatement.
            ?birthPlaceStatement ps:P19 ?lieuNaissance ;
                                wikibase:rank ?rangNaissanceURI .
            BIND(
            IF(?rangNaissanceURI = wikibase:PreferredRank, "Preferred",
            IF(?rangNaissanceURI = wikibase:NormalRank, "Normal",
            IF(?rangNaissanceURI = wikibase:DeprecatedRank, "Deprecated", "Unknown")))
            AS ?rangNaissance
            )
        }}
        OPTIONAL {{
            ?item p:P20 ?deathPlaceStatement.
            ?deathPlaceStatement ps:P20 ?lieuMort ;
                                wikibase:rank ?rangMortURI .
            BIND(
            IF(?rangMortURI = wikibase:PreferredRank, "Preferred",
            IF(?rangMortURI = wikibase:NormalRank, "Normal",
            IF(?rangMortURI = wikibase:DeprecatedRank, "Deprecated", "Unknown")))
            AS ?rangMort
            )
        }}
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,mul,en" . }}
        }}
    """

def load_cache():
    try:
        with open(CACHE_PATH, encoding='utf-8') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_cache(success_qids):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(success_qids), f, ensure_ascii=False, indent=2)

def run_sparql_query(query):
    response = requests.get(SPARQL_ENDPOINT, params={"query": query}, headers=HEADERS, verify=False)
    response.raise_for_status()
    return response.json()

def main():
    os.makedirs(DUMP_DIR, exist_ok=True)  # Création du dossier dump
    all_qids = extract_qids_from_csv(CSV_PATH)
    processed_qids = load_cache()
    remaining_qids = [qid for qid in all_qids if qid not in processed_qids]

    print(f"Total QIDs to process: {len(remaining_qids)}")

    batch_number = 0
    for batch in chunked_iterable(remaining_qids, BATCH_SIZE):
        batch_number += 1
        print(f"Processing batch {batch_number}: {len(batch)} QIDs...")

        try:
            query = build_sparql_query(batch)
            result = run_sparql_query(query)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_path = os.path.join(DUMP_DIR, f"dump_batch_{batch_number}_{timestamp}.json")
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            processed_qids.update(batch)
            save_cache(processed_qids)

        except Exception as e:
            print(f"Erreur lors du traitement du batch {batch_number}: {e}")

        time.sleep(5)  # Pause de 5 secondes entre les requêtes

if __name__ == "__main__":
    main()
