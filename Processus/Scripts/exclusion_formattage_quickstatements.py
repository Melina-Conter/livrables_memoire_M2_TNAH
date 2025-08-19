import pandas as pd
import datetime

ids_alignes_candidats = pd.read_csv("ids_alignes_candidats.csv")
ids_repertoire = pd.read_csv("entites_tms_publiees.csv")
fichier_sortie = "quickstatements_p2268_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
script_sql_statut_publie = "script_sql_statut_publie_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".sql"

# Exclusion des lignes contenant un tms_id non publié dans le répertoire
ids_alignes_candidats = ids_alignes_candidats[ids_alignes_candidats['tms_id'].isin(ids_repertoire['ID'])]

# Création d'un fichier formatté pour QuickStatements
with open(fichier_sortie, "w", encoding="utf-8") as f:
    for index, row in ids_alignes_candidats.iterrows():
        tms_id = row['tms_id']
        wikidata_id = row['qid']
       
        # Format QuickStatements pour ajouter P2268 (ID Orsay) à l'entité Wikidata
        # Syntaxe : QID<TAB>P2268<TAB>"valeur"
        f.write(f"{wikidata_id}\tP2268\t\"{tms_id}\"\n")

print(f"Fichier {fichier_sortie} créé avec {len(ids_alignes_candidats)} déclarations à ajouter.")

# Affichage d'un aperçu des 5 premières lignes du fichier généré
print(f"\nAperçu des 5 premières lignes du fichier généré :")
with open(fichier_sortie, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i < 5:
            print(f"  {line.strip()}")
        else:
            break

# OPTION 1: Une seule requête UPDATE avec IN (recommandée)
liste_ids_publiees_sur_wikidata = ids_alignes_candidats['tms_id'].unique().tolist()

with open(script_sql_statut_publie, "w", encoding="utf-8") as f:
    if liste_ids_publiees_sur_wikidata:
        # Formatage correct de la liste pour SQL
        ids_formatted = "', '".join(str(id) for id in liste_ids_publiees_sur_wikidata)
        sql_query = f"UPDATE app_alignement.table_tms SET statut_validation = 'publie' WHERE tms_id IN ('{ids_formatted}');\n"
        f.write(sql_query)

print(f"\nScript SQL créé : {script_sql_statut_publie}")
print(f"Nombre d'IDs uniques à mettre à jour : {len(liste_ids_publiees_sur_wikidata)}")