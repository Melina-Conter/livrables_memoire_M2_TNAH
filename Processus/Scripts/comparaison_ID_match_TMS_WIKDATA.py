import pandas as pd
import argparse

def compare_csv_files(csv1_path, csv2_path, output_path):
    """
    Compare deux fichiers CSV et crée un nouveau CSV avec une colonne 'match'
    indiquant si l'ID du premier CSV existe dans le second.
    
    Args:
        csv1_path (str): Chemin vers le premier fichier CSV (avec ConstituentID et ConstituentTypeID)
        csv2_path (str): Chemin vers le second fichier CSV (avec seulement IDorsay)
        output_path (str): Chemin pour le fichier CSV de sortie
    """
    # Charger les fichiers CSV
    try:
        df1 = pd.read_csv(csv1_path)
        df2 = pd.read_csv(csv2_path)
    except Exception as e:
        print(f"Erreur lors du chargement des fichiers CSV: {e}")
        return
    
    # Vérifier si les colonnes requises existent
    if 'ConstituentID' not in df1.columns:
        print("Erreur: La colonne 'ConstituentID' n'existe pas dans le premier CSV")
        return
    
    if 'IDorsay' not in df2.columns:
        print("Erreur: La colonne 'IDorsay' n'existe pas dans le second CSV")
        return
    
    # Créer une liste des ID du second CSV
    ids_csv2 = set(df2['IDorsay'].astype(str))
    
    # Ajouter la colonne 'match' au premier DataFrame
    df1['match'] = df1['ConstituentID'].astype(str).apply(lambda x: x in ids_csv2)
    
    # Enregistrer le résultat dans un nouveau fichier CSV
    df1.to_csv(output_path, index=False)
    
    # Afficher un résumé
    total_ids = len(df1)
    matching_ids = df1['match'].sum()
    print(f"\nRésultat de la comparaison:")
    print(f"Total des IDs dans le premier CSV: {total_ids}")
    print(f"IDs correspondants: {matching_ids} ({matching_ids/total_ids*100:.2f}%)")
    print(f"IDs non correspondants: {total_ids - matching_ids} ({(total_ids - matching_ids)/total_ids*100:.2f}%)")
    print(f"\nFichier de sortie créé avec succès: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare deux fichiers CSV basés sur leurs ID.")
    parser.add_argument("csv1", help="Chemin vers le premier fichier CSV (avec ConstituentID)")
    parser.add_argument("csv2", help="Chemin vers le second fichier CSV (avec IDorsay)")
    parser.add_argument("output", help="Chemin pour le fichier CSV de sortie")
    
    args = parser.parse_args()
    
    compare_csv_files(args.csv1, args.csv2, args.output)