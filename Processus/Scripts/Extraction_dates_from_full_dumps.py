import json
import os
import csv

def extraire_dates(qid, claims):
    resultats = []
    for prop, typ in [('P569', 'naissance'), ('P570', 'mort')]:
        if prop not in claims:
            continue
        for claim in claims[prop]:
            mainsnak = claim.get('mainsnak')
            if not mainsnak:
                continue
            datavalue = mainsnak.get('datavalue')
            if not datavalue:
                continue
            valeur = datavalue.get('value')
            if not valeur:
                continue
            date = valeur.get('time')
            if not date:
                continue
            # Nettoyage date (retirer T00:00:00Z si présent)
            date = date.replace('T00:00:00Z', '')
            precision = valeur.get('precision', None)
            rang = claim.get('rank', None)
            resultats.append((qid, typ, date, precision, rang))
    return resultats

def traiter_dossier(dossier_json, chemin_csv_sortie):
    fichiers = [f for f in os.listdir(dossier_json) if f.endswith('.json')]
    total = len(fichiers)
    if total == 0:
        print("Aucun fichier JSON trouvé dans le dossier.")
        return

    with open(chemin_csv_sortie, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['QID', 'type_date', 'date', 'precision', 'rang'])

        for i, fichier in enumerate(fichiers, 1):
            chemin_fichier = os.path.join(dossier_json, fichier)
            try:
                with open(chemin_fichier, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'entities' in data and data['entities']:
                    qid = list(data['entities'].keys())[0]
                    claims = data['entities'][qid].get('claims', {})
                elif 'claims' in data:
                    qid = data.get('id', 'QID_inconnu')
                    claims = data.get('claims', {})
                else:
                    print(f"⚠️ Structure inattendue dans {fichier} - saut du fichier")
                    continue

                dates = extraire_dates(qid, claims)
                for d in dates:
                    writer.writerow(d)

            except Exception as e:
                print(f"Erreur avec le fichier {fichier} : {e}")
                continue

            # Affichage avancement en %
            progress = (i / total) * 100
            print(f"Progression : {progress:.1f}% ({i}/{total})", end='\r')

    print("\nTerminé !")

if __name__ == "__main__":
    dossier_json = r".\json_full_dump_entites"  # modifie ce chemin vers ton dossier
    chemin_csv_sortie = r"dates_naissance_mort_extraction_full_dump.csv"  # modifie ce chemin vers ton CSV

    traiter_dossier(dossier_json, chemin_csv_sortie)
