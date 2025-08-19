import pandas as pd

# Ouverture des CSV - correction des chemins (doubler les backslashes)
alignements_avec_error = pd.read_csv(r"C:\Users\mconter\Downloads\extraction-random-10000-13-05-2025-Openrefine-csv(1).csv")
batch_error_resolu = pd.read_csv(r"C:\Users\mconter\Downloads\batch-error-1689-openrefine-14-05-2025-csv.csv")

# Filtrage du premier CSV - logique inversée pour garder les lignes SANS erreur
alignements_sans_error = alignements_avec_error[~alignements_avec_error["candidats_scores_wikidata"].str.contains('error', case=False, na=False)]

# Fusion des deux CSV
alignements_sans_error_complet = pd.concat([alignements_sans_error, batch_error_resolu], axis=0, ignore_index=True)

# Création du fichier CSV final
alignements_sans_error_complet.to_csv('alignements_sans_error_complet.csv', index=False)

print("Fichiers CSV fusionnés avec succès")