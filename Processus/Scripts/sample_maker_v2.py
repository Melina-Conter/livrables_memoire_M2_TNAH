import pandas as pd
import numpy as np
import random
import os
import math

def create_random_sample_and_sql(
    data_path, 
    sample_size=100, 
    include_types=None, 
    exclude_types=None, 
    seed=42,
    output_file="sample_with_sql.txt"
):
    """
    Crée un échantillon aléatoire de ConstituentIDs et génère une requête SQL.
    Les entités sont réparties équitablement entre les types spécifiés.
    
    Paramètres:
    - data_path: chemin vers le fichier de données (CSV, Excel, etc.)
    - sample_size: taille de l'échantillon souhaité
    - include_types: liste des types à inclure (si None, tous les types sont inclus)
    - exclude_types: liste des types à exclure
    - seed: graine pour la reproductibilité
    - output_file: nom du fichier de sortie pour les IDs et la requête SQL
    
    Retourne:
    - Une liste de ConstituentIDs sélectionnés aléatoirement
    """
    # Définir la graine aléatoire pour la reproductibilité
    random.seed(seed)
    np.random.seed(seed)
    
    # Détecter l'extension du fichier et le charger en conséquence
    if data_path.endswith('.csv'):
        df = pd.read_csv(data_path)
    elif data_path.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(data_path)
    else:
        raise ValueError("Format de fichier non pris en charge. Utilisez CSV ou Excel.")
    
    print(f"Données chargées: {len(df)} lignes trouvées")
    
    # Filtrer les lignes où match est FALSE
    df_filtered = df[df['match'] == False]
    print(f"Après filtrage sur match=FALSE: {len(df_filtered)} lignes")
    
    # Déterminer les types à utiliser
    if include_types:
        # Filtrer le dataframe pour n'inclure que les types spécifiés
        df_filtered = df_filtered[df_filtered['ConstituentTypeID'].isin(include_types)]
        print(f"Après filtrage sur types inclus: {len(df_filtered)} lignes")
        # Utiliser les types spécifiés par l'utilisateur
        types_to_use = include_types
    else:
        # Si aucun type n'est spécifié, utiliser tous les types disponibles
        types_to_use = df_filtered['ConstituentTypeID'].unique().tolist()
        print(f"Aucun type spécifié, utilisation de tous les types disponibles: {len(types_to_use)} types")
    
    if exclude_types:
        df_filtered = df_filtered[~df_filtered['ConstituentTypeID'].isin(exclude_types)]
        # Mettre à jour les types à utiliser après exclusion
        types_to_use = [t for t in types_to_use if t not in exclude_types]
        print(f"Après filtrage sur types exclus: {len(df_filtered)} lignes")
    
    # Vérifier si nous avons des données après filtrage
    if len(df_filtered) == 0:
        raise ValueError("Aucune donnée disponible après application des filtres")
    
    # Obtenir la distribution par type
    type_counts = {}
    for type_id in types_to_use:
        type_data = df_filtered[df_filtered['ConstituentTypeID'] == type_id]
        type_counts[type_id] = len(type_data)
    
    print(f"Distribution des types disponibles après filtrage: {type_counts}")
    
    # Calculer la quantité par type pour une répartition équitable
    num_types = len(types_to_use)
    if num_types == 0:
        raise ValueError("Aucun type disponible après application des filtres")
    
    ids_per_type = math.ceil(sample_size / num_types)
    
    # Sélectionner les IDs pour chaque type
    selected_ids = []
    actual_distribution = {}
    
    for type_id in types_to_use:
        type_data = df_filtered[df_filtered['ConstituentTypeID'] == type_id]
        available_ids = type_data['ConstituentID'].unique()
        
        # Calculer combien d'IDs on peut prendre de ce type
        # Au moins 1, mais pas plus que ce qui est disponible
        target_count = min(ids_per_type, len(available_ids))
        
        if len(available_ids) > 0:
            # Sélectionner aléatoirement des IDs de ce type
            type_ids = random.sample(list(available_ids), target_count)
            selected_ids.extend(type_ids)
            actual_distribution[type_id] = len(type_ids)
        else:
            print(f"Attention: Aucun ID disponible pour le type {type_id}")
            actual_distribution[type_id] = 0
    
    # Si nous avons trop d'IDs, réduire aléatoirement
    if len(selected_ids) > sample_size:
        selected_ids = random.sample(selected_ids, sample_size)
        
        # Recalculer la distribution réelle après réduction
        actual_distribution = {}
        for id_val in selected_ids:
            type_id = df_filtered[df_filtered['ConstituentID'] == id_val]['ConstituentTypeID'].iloc[0]
            actual_distribution[type_id] = actual_distribution.get(type_id, 0) + 1
    
    # Calculer les pourcentages de la distribution finale
    total_selected = len(selected_ids)
    percentage_distribution = {type_id: (count / total_selected * 100) for type_id, count in actual_distribution.items()}
    
    # Afficher la répartition obtenue
    print("\nRépartition obtenue dans l'échantillon:")
    for type_id, count in actual_distribution.items():
        percentage = percentage_distribution[type_id]
        print(f"Type {type_id}: {count} entités ({percentage:.1f}%)")
    
    # Créer la clause IN avec les IDs sélectionnés
    ids_clause = ', '.join(map(str, selected_ids))
    
    # Créer la requête SQL complète
    sql_query = f"""
    WITH DomaineCTE AS (
        SELECT c.ConstituentID,
            c.ConstituentTypeID as Type,
            c.DisplayName AS Nom_complet,
            can1.DisplayName AS Etat_civil,
            can2.LastName AS Nom_de_famille,
            cg1.Locale AS Date_naissance, 
            cg1.City AS Lieu_naissance,
            cg2.Locale AS Date_mort, 
            cg2.City AS Lieu_mort,
            cg3.Lot AS Date_deb_activite,
            cg3.Concession AS Date_fin_activite, 
            cg3.City AS Lieu_activite,
            STRING_AGG(uf.UserFieldName, ';') AS Domaine_activite_concat,
            cg4.Country AS Nationalite
        FROM Constituents c
        LEFT JOIN ConAltNames can1 ON c.ConstituentID = can1.ConstituentID AND can1.NameType LIKE N'état civil'
        LEFT JOIN ConAltNames can2 ON c.ConstituentID = can2.ConstituentID AND can2.NameType LIKE N'Nom Principal'
        LEFT JOIN ConGeography cg1 ON c.ConstituentID = cg1.ConstituentID AND cg1.GeoCodeID = 2
        LEFT JOIN ConGeography cg2 ON c.ConstituentID = cg2.ConstituentID AND cg2.GeoCodeID = 3
        LEFT JOIN ConGeography cg3 ON c.ConstituentID = cg3.ConstituentID AND cg3.GeoCodeID = 4
        LEFT JOIN ConGeography cg4 ON c.ConstituentID = cg4.ConstituentID AND cg4.GeoCodeID = 5
        LEFT JOIN UserFieldXrefs ufx ON c.ConstituentID = ufx.ID AND ufx.ContextID = 40
        LEFT JOIN UserFields uf ON ufx.UserFieldID = uf.UserFieldID AND TRY_CAST(FieldValue AS int) IS NOT NULL AND TRY_CAST(FieldValue AS int) != 0
        WHERE c.ConstituentID IN ({ids_clause})
        GROUP BY c.ConstituentID, c.ConstituentTypeID, c.DisplayName, can1.DisplayName, can2.LastName, 
        cg1.Locale, cg1.City, cg2.Locale, cg2.City, cg3.Lot, cg3.Concession, cg3.City, cg4.Country
    )
    SELECT ConstituentID AS ID,
        Type,
        Nom_complet,
        Etat_civil,
        Nom_de_famille,
        Date_naissance,
        Lieu_naissance,
        Date_mort,
        Lieu_mort,
        Date_deb_activite,
        Date_fin_activite,
        Lieu_activite,
        CASE 
            WHEN Domaine_activite_concat = 'documentation personnalités' THEN NULL
            WHEN Domaine_activite_concat = 'dossier à créer' THEN NULL
            ELSE Domaine_activite_concat
        END AS Domaine_activite,
        Nationalite
    FROM DomaineCTE;"""
    
    # Écrire les IDs et la requête SQL dans un fichier
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("IDs sélectionnés:\n")
        f.write(', '.join(map(str, selected_ids)))
        f.write("\n\n")
        f.write("Distribution par type:\n")
        for type_id, count in actual_distribution.items():
            percentage = percentage_distribution[type_id]
            f.write(f"Type {type_id}: {count} entités ({percentage:.1f}%)\n")
        f.write("\n")
        f.write("Requête SQL:\n")
        f.write(sql_query)
    
    print(f"Échantillon de {len(selected_ids)} IDs créé avec succès.")
    print(f"Les IDs et la requête SQL ont été sauvegardés dans '{output_file}'")
    
    return selected_ids, sql_query

if __name__ == "__main__":
    print("===== GÉNÉRATEUR D'ÉCHANTILLON ET DE REQUÊTE SQL =====")
    
    # Demande interactive du fichier CSV
    csv_file = input("Entrez le nom de votre fichier CSV: ")
    
    # Vérifier si le fichier existe
    if not os.path.exists(csv_file):
        print(f"Erreur: Le fichier {csv_file} n'existe pas.")
        exit(1)
    
    # Demande de la taille de l'échantillon
    try:
        sample_size = int(input("Taille de l'échantillon souhaitée [100]: ") or "100")
    except ValueError:
        print("Valeur non valide. Utilisation de la valeur par défaut: 100")
        sample_size = 100
    
    # Demande des types à inclure UNIQUEMENT
    include_str = input("Types à inclure (séparés par des virgules) [tous]: ")
    if include_str:
        include_types = [int(t.strip()) for t in include_str.split(',') if t.strip().isdigit()]
    else:
        include_types = None

    # Pas de types à exclure désormais
    exclude_types = None
    
    # Nom du fichier de sortie
    output_file = input("Nom du fichier de sortie [sample_with_sql.txt]: ") or "sample_with_sql.txt"
    
    # Graine aléatoire
    try:
        seed = int(input("Graine aléatoire pour reproductibilité [42]: ") or "42")
    except ValueError:
        print("Valeur non valide. Utilisation de la valeur par défaut: 42")
        seed = 42
    
    # Exécution de la fonction
    try:
        selected_ids, sql_query = create_random_sample_and_sql(
            data_path=csv_file,
            sample_size=sample_size,
            include_types=include_types,
            exclude_types=exclude_types,
            seed=seed,
            output_file=output_file
        )
        
        print(f"\nAperçu des 5 premiers IDs sélectionnés: {selected_ids[:5]}...")
        print(f"Requête SQL générée et sauvegardée dans {output_file}")
        
    except Exception as e:
        print(f"Une erreur s'est produite: {e}")