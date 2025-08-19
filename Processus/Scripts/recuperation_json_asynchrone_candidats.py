import requests
import pandas as pd
import re
import time
from pathlib import Path
import json
import warnings
import urllib3
import shutil

# Désactivation des avertissements
warnings.filterwarnings('ignore', category=FutureWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CSV_FILE = 'alignements_sans_error_complet.csv'
CACHE_FILE = 'wikidata_cache_asynchrone.json'
CACHE_BACKUP_FILE = 'wikidata_cache_asynchrone.json.bak'
DUMP_DIR = Path('json_full_dump_entites')
DUMP_DIR.mkdir(exist_ok=True)
REQUEST_DELAY = 0  # Réduit à 0 pour désactiver le délai
last_request_time = 0

# Utilisation d'une session HTTP pour optimiser les connexions
session = requests.Session()

# Chargement du cache existant (liste de QID déjà traités)
if Path(CACHE_FILE).exists():
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = set(json.load(f))
    except json.JSONDecodeError:
        print("⚠️ Cache corrompu, tentative de récupération partielle...")
        with open(CACHE_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
            raw = raw.strip().rstrip(',]}') + ']'  # tentative de réparation en liste
        try:
            cache = set(json.loads(raw))
        except Exception as e:
            print(f"Erreur irrécupérable du cache : {e}")
            cache = set()
else:
    cache = set()

def save_cache():
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(cache), f, ensure_ascii=False, indent=2)
    shutil.copy(CACHE_FILE, CACHE_BACKUP_FILE)

def get_entity_data(qid):
    global last_request_time, cache
    
    if qid in cache:
        # Déjà traité, on peut juste charger le fichier correspondant s'il est utile
        dump_path = DUMP_DIR / f"{qid}.json"
        if dump_path.exists():
            with open(dump_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Si fichier manquant, forcer nouvelle requête
            cache.remove(qid)
    
    if not qid or pd.isna(qid):
        return None
    
    entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    
    elapsed = time.time() - last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)

    try:
        response = session.get(entity_url, timeout=30, verify=False)
        last_request_time = time.time()

        if response.status_code == 429:
            print(f"Trop de requêtes pour {qid}, pause de 10s...")
            time.sleep(10)
            return get_entity_data(qid)
        if response.status_code != 200:
            print(f"Erreur HTTP {response.status_code} pour {qid}")
            return None

        data = response.json()
        entity_data = data.get('entities', {}).get(qid, {})

        # Sauvegarder dans un fichier JSON par QID
        dump_path = DUMP_DIR / f"{qid}.json"
        with open(dump_path, 'w', encoding='utf-8') as f:
            json.dump(entity_data, f, ensure_ascii=False, indent=2)

        # Ajouter au cache
        cache.add(qid)
        save_cache()

        return entity_data

    except Exception as e:
        print(f"Erreur lors de la requête pour {qid}: {str(e)}")
        return None

def extract_candidates(candidate_str):
    if pd.isna(candidate_str) or 'candidats' not in str(candidate_str):
        return []
    
    pattern = r"\('(Q\d+)', ([\d\.]+)\)"
    matches = re.findall(pattern, str(candidate_str))
    return matches

def expand_candidates(row):
    result = []
    original_index = row.name
    candidates = extract_candidates(row['candidats_scores_wikidata'])
    
    if not candidates:
        return pd.DataFrame({
            'original_index': [original_index],
            'qid': [None],
            'score': [None]
        })
    
    for qid, score in candidates:
        result.append({
            'original_index': original_index,
            'qid': qid,
            'score': float(score)
        })
    
    return pd.DataFrame(result)

print("📄 Chargement du fichier CSV...")
try:
    csv_avec_candidats = pd.read_csv(CSV_FILE)
    print(f"✅ Fichier chargé. {len(csv_avec_candidats)} lignes.")
except Exception as e:
    print(f"❌ Erreur lors du chargement du CSV : {str(e)}")
    exit(1)

print("🧩 Expansion des candidats...")
df_candidats = pd.concat(
    [df for df in (expand_candidates(row) for _, row in csv_avec_candidats.iterrows()) if not df.empty],
    ignore_index=True
)
print(f"✅ Expansion terminée. {len(df_candidats)} candidats extraits.")

print("🔍 Récupération des données Wikidata...")

for idx, (_, row) in enumerate(df_candidats.iterrows(), start=1):
    qid = row['qid']
    if not qid:
        continue
    entity_data = get_entity_data(qid)
    # Optionnel : exploiter entity_data ici

    progress = int((idx / len(df_candidats)) * 100)
    print(f"\rProgression : {progress}% ({idx}/{len(df_candidats)})", end='', flush=True)

print("\n✅ Récupération terminée.")
