import os
import json
import csv

# Dossier contenant les dumps JSON
dossier_json = ".\dumps_sparql_lieux_avec_rangs"
fichier_sortie = "QID_lieux_rangs.csv"
fichier_sortie_sans_lieu = "QID_sans_lieux.csv"  # Nouveau fichier pour les QID sans lieu

donnees_csv = []
donnees_sans_lieu = []  # Nouvelle liste pour stocker les QID sans lieu
fichiers_traites = 0
fichiers_erreurs = 0
entites_rencontrees = set()  # QID de toutes les entités vues
entites_ajoutees = set()     # QID des entités ajoutées au CSV

def get_qid(uri):
    return uri.split("/")[-1]

# Vérifier que le dossier existe
if not os.path.exists(dossier_json):
    print(f"❌ Erreur : Le dossier '{dossier_json}' n'existe pas")
    exit(1)

for fichier in os.listdir(dossier_json):
    if fichier.endswith(".json"):
        chemin_fichier = os.path.join(dossier_json, fichier)
        
        try:
            # Tentative de lecture du fichier JSON
            with open(chemin_fichier, encoding="utf-8") as f:
                data = json.load(f)
            
            # Vérifier la structure attendue
            if "results" not in data:
                print(f"⚠️  Avertissement : '{fichier}' - Structure inattendue (pas de 'results')")
                continue
                
            if "bindings" not in data.get("results", {}):
                print(f"⚠️  Avertissement : '{fichier}' - Structure inattendue (pas de 'bindings')")
                continue

            # Traitement des données
            items_traites = 0
            for item in data["results"]["bindings"]:
                try:
                    # Vérifier que l'item a bien une clé "item"
                    if "item" not in item:
                        continue
                        
                    qid = get_qid(item["item"]["value"])
                    entites_rencontrees.add(qid)  # Compter toutes les entités vues
                    
                    entite_ajoutee = False  # Flag pour savoir si cette entité sera ajoutée

                    # Si lieuNaissanceLabel présent
                    if "lieuNaissanceLabel" in item:
                        lieu_nom = item["lieuNaissanceLabel"]["value"]
                        rang = item.get("rangNaissance", {}).get("value", "Unknown")
                        donnees_csv.append({
                            "QID": qid,
                            "type_lieu": "naissance",
                            "nom_lieu": lieu_nom,
                            "rang": rang
                        })
                        items_traites += 1
                        entite_ajoutee = True

                    # Si lieuMortLabel présent
                    if "lieuMortLabel" in item:
                        lieu_nom = item["lieuMortLabel"]["value"]
                        rang = item.get("rangMort", {}).get("value", "Unknown")
                        donnees_csv.append({
                            "QID": qid,
                            "type_lieu": "mort",
                            "nom_lieu": lieu_nom,
                            "rang": rang
                        })
                        items_traites += 1
                        entite_ajoutee = True
                    
                    # Si l'entité a été ajoutée au moins une fois, l'ajouter au set
                    if entite_ajoutee:
                        entites_ajoutees.add(qid)
                        
                except Exception as e:
                    print(f"⚠️  Erreur lors du traitement d'un item dans '{fichier}': {e}")
                    continue
            
            print(f"✅ '{fichier}' traité - {items_traites} entrées ajoutées")
            fichiers_traites += 1
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur JSON dans '{fichier}': {e}")
            fichiers_erreurs += 1
            
        except FileNotFoundError:
            print(f"❌ Fichier non trouvé : '{fichier}'")
            fichiers_erreurs += 1
            
        except UnicodeDecodeError as e:
            print(f"❌ Erreur d'encodage dans '{fichier}': {e}")
            fichiers_erreurs += 1
            
        except Exception as e:
            print(f"❌ Erreur inattendue avec '{fichier}': {e}")
            fichiers_erreurs += 1

# Créer la liste des QID sans lieu (ceux rencontrés mais non ajoutés)
qid_sans_lieu = entites_rencontrees - entites_ajoutees
donnees_sans_lieu = [{"QID": qid} for qid in qid_sans_lieu]

# Tentative d'écriture des CSV
try:
    # Écrire le fichier principal avec les lieux
    with open(fichier_sortie, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["QID", "type_lieu", "nom_lieu", "rang"])
        writer.writeheader()
        writer.writerows(donnees_csv)
    
    # Écrire le nouveau fichier avec les QID sans lieu
    with open(fichier_sortie_sans_lieu, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["QID"])
        writer.writeheader()
        writer.writerows(donnees_sans_lieu)
    
    print(f"\n✅ Fichier CSV écrit : {fichier_sortie}")
    print(f"✅ Fichier CSV des QID sans lieu écrit : {fichier_sortie_sans_lieu}")
    print(f"📊 Statistiques :")
    print(f"   - Fichiers traités avec succès : {fichiers_traites}")
    print(f"   - Fichiers avec erreurs : {fichiers_erreurs}")
    print(f"   - Nombre total de lignes dans le CSV des lieux : {len(donnees_csv)}")
    print(f"   - Nombre total de QID sans lieu : {len(donnees_sans_lieu)}")
    print(f"\n🏷️  Résumé des entités :")
    print(f"   - Entités rencontrées au total : {len(entites_rencontrees)}")
    print(f"   - Entités ajoutées au CSV des lieux : {len(entites_ajoutees)}")
    print(f"   - Entités sans lieu : {len(entites_rencontrees) - len(entites_ajoutees)}")
    
    
except PermissionError:
    print(f"❌ Erreur : Impossible d'écrire les fichiers (permissions insuffisantes)")
    
except Exception as e:
    print(f"❌ Erreur lors de l'écriture des CSV : {e}")