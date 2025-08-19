import csv
import os
from datetime import datetime

def detecter_delimiteur(fichier_source):
    """
    Détecte le délimiteur utilisé dans un fichier CSV
    
    Args:
        fichier_source (str): Chemin vers le fichier CSV source
        
    Returns:
        str: Le délimiteur détecté (virgule, point-virgule, tabulation)
    """
    with open(fichier_source, 'r', encoding='utf-8') as f:
        premiere_ligne = f.readline().strip()
        
        # Compter les occurrences des délimiteurs courants
        nb_virgules = premiere_ligne.count(',')
        nb_pointvirgules = premiere_ligne.count(';')
        nb_tabs = premiere_ligne.count('\t')
        
        # Identifier le délimiteur le plus fréquent
        if nb_pointvirgules > nb_virgules and nb_pointvirgules > nb_tabs:
            return ';'
        elif nb_tabs > nb_virgules and nb_tabs > nb_pointvirgules:
            return '\t'
        else:
            return ','

def extraire_lignes_erreur(fichier_source, colonne_erreur="candidat_score_wikidata"):
    """
    Extrait les lignes d'un CSV dont une colonne spécifique contient une erreur
    
    Args:
        fichier_source (str): Chemin vers le fichier CSV source
        colonne_erreur (str): Nom de la colonne à vérifier pour les erreurs
        
    Returns:
        list: Liste des lignes contenant des erreurs
        list: En-têtes du CSV
        str: Délimiteur détecté
    """
    lignes_erreur = []
    
    # Détecter le délimiteur utilisé dans le fichier
    delimiteur = detecter_delimiteur(fichier_source)
    print(f"Délimiteur détecté : '{delimiteur}'")
    
    with open(fichier_source, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiteur)
        headers = next(reader)  # Lire les en-têtes
        
        # Trouver l'index de la colonne d'erreur
        try:
            index_colonne = headers.index(colonne_erreur)
        except ValueError:
            print(f"Erreur : La colonne '{colonne_erreur}' n'existe pas dans le CSV.")
            print(f"Colonnes disponibles : {headers}")
            return [], [], delimiteur
        
        # Parcourir toutes les lignes et extraire celles avec erreur
        for ligne in reader:
            if ligne and len(ligne) > index_colonne:
                valeur = ligne[index_colonne].strip()
                if valeur.lower().startswith("error"):
                    lignes_erreur.append(ligne)
    
    return lignes_erreur, headers, delimiteur

def enregistrer_erreurs(lignes_erreur, headers, delimiteur):
    """
    Enregistre les lignes d'erreur dans un nouveau fichier CSV
    
    Args:
        lignes_erreur (list): Liste des lignes contenant des erreurs
        headers (list): En-têtes du CSV
        delimiteur (str): Délimiteur à utiliser dans le fichier de sortie
    """
    if not lignes_erreur:
        print("Aucune erreur trouvée.")
        return
    
    # Créer un nom de fichier avec la date actuelle
    aujourd_hui = datetime.now()
    date_str = aujourd_hui.strftime("%d_%m_%Y")
    nb_lignes = len(lignes_erreur)
    nom_fichier = f"batch_error_{nb_lignes}_openrefine_{date_str}.csv"
    
    # Écrire les lignes d'erreur dans le nouveau fichier
    with open(nom_fichier, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=delimiteur)
        writer.writerow(headers)  # Écrire les en-têtes
        writer.writerows(lignes_erreur)  # Écrire les lignes d'erreur
    
    print(f"{nb_lignes} lignes avec erreur ont été extraites et sauvegardées dans '{nom_fichier}'")

def main():
    # Demander le chemin du fichier CSV source
    fichier_source = input("Entrez le chemin du fichier CSV source : ")
    
    # Vérifier si le fichier existe
    if not os.path.isfile(fichier_source):
        print(f"Erreur : Le fichier '{fichier_source}' n'existe pas.")
        return
    
    # Demander le nom de la colonne (ou utiliser la valeur par défaut)
    colonne_erreur = input("Entrez le nom de la colonne à vérifier (par défaut: candidat_score_wikidata) : ")
    if not colonne_erreur:
        colonne_erreur = "candidat_score_wikidata"
    
    # Extraire et enregistrer les lignes avec erreur
    lignes_erreur, headers, delimiteur = extraire_lignes_erreur(fichier_source, colonne_erreur)
    enregistrer_erreurs(lignes_erreur, headers, delimiteur)

if __name__ == "__main__":
    main()