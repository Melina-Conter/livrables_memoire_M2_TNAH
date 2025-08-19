# DOCUMENTATION PROCESSUS ALIGNEMENT

### Table des matières :
- [DOCUMENTATION PROCESSUS ALIGNEMENT](#documentation-processus-alignement)
    - [Table des matières :](#table-des-matières-)
  - [I. Génération des candidats](#i-génération-des-candidats)
    - [1. Extraction des données depuis le serveur PRA avec des requêtes SQL](#1-extraction-des-données-depuis-le-serveur-pra-avec-des-requêtes-sql)
      - [a. Les données pour OpenRefine](#a-les-données-pour-openrefine)
      - [b. Le nombre de liens à la création par entité TMS](#b-le-nombre-de-liens-à-la-création-par-entité-tms)
    - [2. Projet OpenRefine](#2-projet-openrefine)
      - [a. Quelques traitement de données](#a-quelques-traitement-de-données)
      - [b. Utilisation de l'API de Réconciliation Wikidata fr (W3C)](#b-utilisation-de-lapi-de-réconciliation-wikidata-fr-w3c)
      - [c. Extraction des résultats de l'API](#c-extraction-des-résultats-de-lapi)
      - [d. Export du projet en csv](#d-export-du-projet-en-csv)
  - [II. Construction de la base principale Postgre pour l'application](#ii-construction-de-la-base-principale-postgre-pour-lapplication)
    - [1. Prétraitements des candidats](#1-prétraitements-des-candidats)
      - [a. Récupération des données Wikidata pour chaque candidat](#a-récupération-des-données-wikidata-pour-chaque-candidat)
        - [a.1. Les dates](#a1-les-dates)
        - [a.2. Les Lieux](#a2-les-lieux)
      - [b. Exclusion des candidats ayant des dates avec un écart de + de 100 ans avec celles de TMS](#b-exclusion-des-candidats-ayant-des-dates-avec-un-écart-de--de-100-ans-avec-celles-de-tms)
    - [2. Récupération des entités déjà alignées sur Wikidata](#2-récupération-des-entités-déjà-alignées-sur-wikidata)
    - [3. Construction des tables](#3-construction-des-tables)
      - [a. Création des CSV de base pour les différentes tables](#a-création-des-csv-de-base-pour-les-différentes-tables)
      - [b. Calcul des flags des données principales pour l'affichage dans l'application](#b-calcul-des-flags-des-données-principales-pour-laffichage-dans-lapplication)
    - [4. Création de la base de l'application dans DBeaver](#4-création-de-la-base-de-lapplication-dans-dbeaver)
      - [a. Création d'un schéma dédié sur le serveur Postgre du serveur LAB](#a-création-dun-schéma-dédié-sur-le-serveur-postgre-du-serveur-lab)
      - [b. Création des tables à partir des csv](#b-création-des-tables-à-partir-des-csv)
        - [b.1. Import des csv et complétion des tables importées](#b1-import-des-csv-et-complétion-des-tables-importées)
        - [b.2. Création des tables utilisateur et historique](#b2-création-des-tables-utilisateur-et-historique)
        - [b.3. Rajouter les contraintes de clés étrangères](#b3-rajouter-les-contraintes-de-clés-étrangères)
  - [III. Création d'une table des données TMS pour l'affichage dans l'application](#iii-création-dune-table-des-données-tms-pour-laffichage-dans-lapplication)
  - [IV. Inscription des alignements sur Wikidata](#iv-inscription-des-alignements-sur-wikidata)
    - [1. Personnes et Institutions alignées et publiées sur le répertoire des artistes et personnalités](#1-personnes-et-institutions-alignées-et-publiées-sur-le-répertoire-des-artistes-et-personnalités)
      - [a. Récupération des ids TMS avec le `statut_validation` "aligne" et du ou des candidats validés (une ligne par paire TMS-candidat distincte)](#a-récupération-des-ids-tms-avec-le-statut_validation-aligne-et-du-ou-des-candidats-validés-une-ligne-par-paire-tms-candidat-distincte)
      - [b. Récupération des ids TMS publiés sur le répertoire](#b-récupération-des-ids-tms-publiés-sur-le-répertoire)
      - [c. Exclusion des ids TMS non publiés sur le répertoire et fromatagepour Quickstatements](#c-exclusion-des-ids-tms-non-publiés-sur-le-répertoire-et-fromatagepour-quickstatements)
      - [d. Inscription via Quickstatements](#d-inscription-via-quickstatements)
      - [e. Mise à jour du statut\_validation des entités TMS concernées](#e-mise-à-jour-du-statut_validation-des-entités-tms-concernées)
    - [2. Personnes et institutions non-alignées et publiées sur le répertoire des artistes et personnalités](#2-personnes-et-institutions-non-alignées-et-publiées-sur-le-répertoire-des-artistes-et-personnalités)
    - [3. Personnes et institutions non publiées dans le répertoire des artistes et personnalités](#3-personnes-et-institutions-non-publiées-dans-le-répertoire-des-artistes-et-personnalités)
      - [a. Les entités TMS alignées](#a-les-entités-tms-alignées)
      - [b. Les entités TMS non alignées](#b-les-entités-tms-non-alignées)
  - [V. Import de nouvelles entités TMS dans la base de 2AMO](#v-import-de-nouvelles-entités-tms-dans-la-base-de-2amo)
  - [LISTE DES SCRIPTS ET DOCUMENTS CITES](#liste-des-scripts-et-documents-cites)
    - [Scripts](#scripts)
    - [Documents](#documents)

## I. Génération des candidats
Voir le [schéma global](./Schemas/schema_global_processus_alignement.png) du processus d'alignement
### 1. Extraction des données depuis le serveur PRA avec des requêtes SQL ###
#### a. Les données pour OpenRefine 
**Pour X entités en hasard** (X étant un nombre à déterminer) : 
- Requête SQL de récupération de tous les IDs TMS dans le serveur PRA :
  ```sql
	SELECT ConstituentID 
	FROM Constituents;
  ```
- Export du résultat en csv
- Utiliser le [script dédié à la récupération d'entités au hasard et la génération de la requête SQL](./Scripts/sample_maker_v2.py). 

Paramètres du script :
  - nom/chemin du csv avec toutes les ID
  - nom/chemin voulu pour le fichier .txt de sortie pour les IDs et la requête SQL générée
  - Liste des types inclus et liste des types exclus (les types correspondent aux valeurs possibles la colonne `ConstituentTypeID`, pour leur signification, voir la table `ConstituentTypes`).
  
Sortie du script :
  - Format : .txt
  - Contenu : 
    - Liste des IDs sélectionnés
    - Distribution des IDs sélectionnés par types
    - Requête SQL

Pour une **liste d'entités déjà déterminée** : utiliser la requête SQL ci-dessous sur le serveur PRA en remplaçant "liste, des, IDs..." par la liste des ID TMS des dites entités.

```sql
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
        WHERE c.ConstituentID IN ('Liste, des, IDs...')
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
    FROM DomaineCTE;
```
>Autres options : 
>- Rajouter une possibilité pour exclure des ID TMS à partir d'une liste d'ID exclus (permettrait d'éviter de traiter les entités déjà présentes dans l'application)
>- Possibilité de sélectionner les données directement dans la table extraite du PRA sur le serveur lab, schema `main`, table `tms-constituent_constituent-description` au lieu de passer par la requête complète mais du coup traitement des données différent à prévoir dans OpenRefine.

---
#### b. Le nombre de liens à la création par entité TMS
Requête SQL à executer sur le serveur PRA : 
```sql
SELECT c.ConstituentID,
       COUNT(DISTINCT r.RoleID) AS nb_roles_creation
FROM Constituents c
LEFT JOIN vgsdvConXRefs_Details vcxd
    ON c.ConstituentID = vcxd.ConstituentID
LEFT JOIN ConXrefs cx
    ON cx.ConXrefID = vcxd.ConXrefID
LEFT JOIN Roles r
    ON r.RoleID = cx.RoleID
WHERE r.RoleTypeID = 1 
GROUP BY c.ConstituentID
ORDER BY COUNT(DISTINCT r.RoleID) DESC;
``` 
Récupérer les résultats en csv.


### 2. Projet OpenRefine
[Dossier Projet openrefine](./Projet_OpenRefine/)

#### a. Quelques traitement de données 
Traitements réalisés :
- Exclusion et corrections de certaines valeurs (RegEx):
  - date_naissance / date_mort : suppression des str "en " et "vers "
	> Si utilisation de la table `tms-constituent_constituent-description` : étapes différentes à définir car il faut alors sélectionner/traiter les dates de naissance et de mort pour qu'elles répondent aux specs de l'API.
  - Domaines_activite : suppression des str documentation personnalités | extérieure, sans dossier, dossier à créer, autre documentation
  - Roles (liens à la création) : suppression des str producteur de fonds, exécutant, anciennement attribué à, attribué à, D'après, atelier de, praticien, genre de.
  - Nationalité : remplacement des str "Russie, Fédération de" par "Russie"
  - Toutes les colonnes : suppression des espaces inutiles
- Déballage des colonnes agrégées en une valeur par colonne (split):
  > Si utilisation de la table `tms-constituent_constituent-description` : étapes différentes à définir car il faut alors déballer des formats json.
  - Colonnes concernées : Roles, Nationalites, Domaines_activite
  - Méthode utilisée dans le projet : formule python.

#### b. Utilisation de l'API de Réconciliation Wikidata fr (W3C)
- Réconciliation à partir de la colonne `DisplayName`, choisir l'API de réconciliation Wikidata fr.
- Mapping des données dans OpenRefine vers les propriétés Wikidata
  > Voir le [mapping](./Mapping_TMS_wikidata.xlsx) réalisé en amont
  - Pour les colonnes déballées : mappage des colonnes issues d'une même colonne agrégée avec la même propriété correspondante.
  - Ne pas mapper ConstituentID
- Paramètres : 
  - Réconcilier avec le type : `personne ou organisation` (Q106559804) si l'on traite aussi bien des personnes morales que physique.
  - Pas de nombre maximal de candidat envoyé

> Potentielle évolution future : Utiliser l'API directement en script python ([voir specs de l'API](https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/)) et les ([notes sur son fonctionnement](../Notes_et_observations/propriétés_api_reconciliation.docx)) au lieu de passer par OpenRefine. Il faudra cependant réaliser des tests de masse pour savoir en quelles proportions fractionner les queries afin de ne pas obtenir trop d'erreurs. OpenRefine gère le fractionnement de façon autonome.

#### c. Extraction des résultats de l'API
Formule python pour extraire les QID des candidats et leur score dans une nouvelle colonne à partir de la colonne `DisplayName` :
```python
	if hasattr(cell.recon, 'error') and cell.recon.error:
    return "error : " + cell.recon.error
	elif not cell.recon.candidates or len(cell.recon.candidates) == 0:
		return ""
	else:
		candidates_list = []
		for candidate in cell.recon.candidates:
			candidates_list.append("('" + candidate.id + "', " + str(candidate.score) + ")")
		
		return "{candidats : [" + ", ".join(candidates_list) + "]}"
```

Dans le cas où le processus de réconciliation aurait provoqué des erreurs : la nouvelle colonne `candidats_scores_wikidata` contiendra alors des messages ressemblant à `error : [type d'erreur]`. L'occurrence d'erreurs dépend grandement de la stabilité du service de l'API qui peut avoir des faiblesses de temps à autre.

#### d. Export du projet en csv
[Aperçu de l'export final OpenRefine](alignements_sans_error_complet.csv)

S'il y eu des erreurs générées par le processus de réconciliation : 
- créer un nouveau csv qui ne garde que les lignes concernées par des messages d'erreur ([voir script dédié](./Scripts/recup_batch_error.py)).
- Importer le csv en tant que nouveau projet dans OpenRefine
- Supprimer la colonne `candidats_scores_wikidata`
- Relancer le [processus de réconciliation avec l'API wikidata fr](#b-utilisation-de-lapi-de-réconciliation-wikidata-fr-w3c) et [extraire les QID et score des candidats](#c-extraction-des-résultats-de-lapi).
- Exporter le projet OpenRefine en csv et remplacer les lignes avec des erreurs dans le premier export de projet par celle de ce deuxième export ([voir script dédié](./Scripts/fusion_batch_error_et_premier_batch.py))
- S'il y a encore des erreurs : répéter les étapes précédentes jusqu'à ce que le processus de réconciliation n'en génère plus.

## II. Construction de la base principale Postgre pour l'application

### 1. Prétraitements des candidats

#### a. Récupération des données Wikidata pour chaque candidat
##### a.1. Les dates
[Le script de téléchargement des données des candidats](./Scripts/recuperation_json_asynchrone_candidats.py)

Fonctionnement : 
- Extraction des QIDS et scores API de la colonne `candidats_scores_wikidata`
- Téléchargement des données des candidats via `https://www.wikidata.org/wiki/Special:EntityData/{qid}.json`.
- création d'un dossier pour y stocker les fichiers json.
- Création d'un cache et d'un backup de cache en cas d'interruption du script et/ou corruption du cache.

| Paramètres | Description | Format/Type |
| --- | --- | --- |
| CSV_FILE | Chemin du csv final OpenRefine. Doit contenir la colonne `candidats_scores_wikidata` qui stocke les identifiants Wikidata (QID) et leurs scores renvoyés par l'API. | `.csv` |
| CACHE_FILE | Chemin du fichier créé pour stocker le cache. | `.json` |
| CACHE_BACKUP_FILE | Chemin du fichier créé pour le backup du cache (en cas d'interruption de script). | `.json.bak` |
| DUMP_DIR | Path (chemin du répertoire dans lequel les full dumps seront stockés). | `/dir` |
| DUMP_DIR.mkdir(exist_ok=True) | Activaton ou désactivation de la condition d'existence du dossier de stockage pour les full dumps. | `bool` |
| REQUEST_DELAY | Délais en secondes entre chaque requête HTTP. Permet d'éviter les erreur de time out. | `int` |
| last_request_time | Variable globale pour tracker le timestamp de la dernière requête HTTP, utilisée avec REQUEST_DELAY pour contrôler le rythme des appels. Initialisée à 0. |  `float` |

---

[Le script d'extraction des dates](./Scripts/Extraction_dates_from_full_dumps.py)

Fonctionnement :
- Parcourt tous les fichiers JSON du dossier spécifié contenant les full dumps des candidats
- Extrait les dates de [naissance (P569)](https://www.wikidata.org/wiki/Property:P569) et de [mort (P570)](https://www.wikidata.org/wiki/Property:P570) avec leur précision et leur rang
- Nettoie les dates en supprimant le suffixe "T00:00:00Z"
- Sauvegarde les résultats dans un fichier CSV avec indicateur de progression
- Gère les structures JSON variées (avec ou sans clé 'entities')

| Paramètres | Description | Format/Type |
| --- | --- | --- |
| dossier_json | Chemin du dossier contenant les fichiers JSON des full dumps | `str` |
| chemin_csv_sortie | Chemin du fichier de sortie pour les dates extraites | `.csv` |
| prop | Propriétés Wikidata : P569 (naissance), P570 (mort) | `str` |
| typ | Type de date : 'naissance' ou 'mort' | `str` |

Structure du fichier de sortie :

| Colonne | Description | Type |
| --- | --- | --- |
| QID | Identifiant Wikidata de l'entité | `str` |
| type_date | Type de date ('naissance' ou 'mort') | `str` |
| date | Date extraite (format ISO, nettoyée) | `str` |
| precision | Précision de la date selon Wikidata | `int` |
| rang | Rang de la déclaration dans Wikidata | `str` |

##### a.2. Les Lieux 
[Le script de téléchargement des labels et rangs des lieux de naissance et de mort](./Scripts/recuperation_json_lieux_only_batchs_sparql.py)

Fonctionnement :
- Extraction des QID des candidats de la colonne `candidats_scores_wikidata`
- Regroupe les QID par paquets dont la quantité est définiepar BATCH_SIZE
- Exécute une requête SPARQL par paquet pour récupérer les lieux de [naissance(P19)](https://www.wikidata.org/wiki/Property:P19) et de [mort(P20)](https://www.wikidata.org/wiki/Property:P20) des candidats avec leur rang. Les requêtes sont espacées de 5 sec pour éviter les erreurs de time out. 
- création d'un dossier pour y stocker les résultats des requêtes en json.
- Création d'un cache au fur et à mesure des requêtes en cas d'interruption de script.


| Paramètres | Description | Format/Type |
| --- | --- | --- |
| SPARQL_ENDPOINT | URL de l'endpoint SPARQL de Wikidata : [`https://query.wikidata.org/sparql`](https://query.wikidata.org/sparql) | `str` |
| CSV_PATH | Chemin du csv final OpenRefine. | `.csv` |
| CACHE_PATH | Chemin du fichier créé pour stocker le cache. | `.json` |
| DUMP_DIR | Chemin du répertoire dans lequel les full dumps seront stockés. | `/dir` |
| BATCH_SIZE | Nombre de QID traités simultanément dans une seule requête SPARQL (50 par défaut) pour optimiser les performances et respecter les limites de l'API. | `int` |
| HEADERS | Dictionnaire contenant les en-têtes HTTP spécifiant le format de réponse souhaité (JSON) pour les requêtes SPARQL. | `dict` |

---

[Le script d'extraction des labels et rangs des lieux de naissance et de mort](./Scripts/Extraction_lieux_et_rang_from_batch_sparql.py)

Fonctionnement :
- Parcourt tous les fichiers JSON du dossier contenant les résultats des requêtes SPARQL
- Extrait les lieux de naissance et de mort avec leurs labels et rangs
- Sépare les entités ayant des lieux de celles n'en ayant pas
- Génère deux fichiers CSV : un avec les lieux et un avec les QID sans lieu
- Gère les erreurs de format JSON et d'encodage avec rapports détaillés
- Fournit des statistiques complètes sur le traitement

| Paramètres | Description | Format/Type |
| --- | --- | --- |
| dossier_json | Chemin du répertoire contenant les dumps JSON SPARQL | `/dir` |
| fichier_sortie | Nom du fichier CSV de sortie principal (avec lieux) | `.csv` |
| fichier_sortie_sans_lieu | Nom du fichier CSV pour les QID sans lieu | `.csv` |
| entites_rencontrees | Set des QID de toutes les entités rencontrées | `set` |
| entites_ajoutees | Set des QID des entités ajoutées au CSV des lieux | `set` |

Structure du fichier de sortie principal :

| Colonne | Description | Type |
| --- | --- | --- |
| QID | Identifiant Wikidata du candidat | `str` |
| type_lieu | Type de lieu ('naissance' ou 'mort') | `str` |
| nom_lieu | Label du lieu en français | `str` |
| rang | Rang de la déclaration dans Wikidata | `str` |

Structure du fichier de sortie des QID sans lieu :

| Colonne | Description | Type |
| --- | --- | --- |
| QID | Identifiant Wikidata du candidat sans lieu | `str` |


  
#### b. Exclusion des candidats ayant des dates avec un écart de + de 100 ans avec celles de TMS
[Le script comparaison des dates TMS-Wikidata et exclusion des candidats non alignables](./Scripts/comparaison_dates.py)

Fonctionnement :
- Compare les dates de naissance et de mort extraites des alignements avec celles de Wikidata
- Parse et normalise les dates dans différents formats (AAAA, AAAA-MM, JJ/MM/AAAA, etc.)
- Gère les dates historiques anciennes et les précisions variables
- Calcule les écarts en années entre les dates de TMS et Wikidata
- Génère des visualisations des écarts par tranche et par rang de déclaration
- Identifie et exclut les QID qui n'ont que des dates présentant des écarts > 100 ans avec TMS
- Produit des rapports détaillés avec logging des erreurs

| Paramètres | Description | Format/Type |
| --- | --- | --- |
| fichier_alignement | Chemin du csv final OpenRefine. | `.csv` |
| fichier_dates_wikidata | Fichier des dates extraites de Wikidata | `.csv` |
| fichier_ecarts | Fichier de sortie avec tous les écarts calculés | `.csv` |
| fichier_ecarts_sup_100 | Fichier  des écarts supérieurs à 100 ans | `.csv` |
| fichier_ecarts_inf_100 | Fichier des écarts inférieurs ou égaux à 100 ans | `.csv` |
| fichier_graphique | Graphique de visualisation des écarts | `.png` |
| fichier_exclusion | Fichier des QID exclus (écarts > 100 ans uniquement) | `.csv` |
| log_file | Fichier de log pour tracer les erreurs et avertissements | `.log` |
| PRECISION_WIKIDATA | Dictionnaire de conversion des précisions numériques Wikidata | `dict` |

Structure du fichier de sortie principal (écarts) :

| Colonne | Description | Type |
| --- | --- | --- |
| ID_alignement | Identifiant de l'entité TMS dans le fichier d'alignement | `str` |
| QID | Identifiant Wikidata de l'entité | `str` |
| Rang | Rang de la déclaration dans Wikidata (normal, preferred, deprecated) | `str` |
| Type_date | Type de date ('naissance' ou 'mort') | `str` |
| Date_alignement | Date originale du fichier d'alignement | `str` |
| Date_wikidata | Date formatée ISO de Wikidata | `str` |
| Precision_align | Précision de la date d'alignement (9=année, 10=mois, 11=jour) | `int` |
| Precision_wikidata | Précision de la date Wikidata (lisible) | `str` |
| Ecart_annees | Écart calculé en années entre les deux dates | `int` |

Structure du fichier d'exclusion :

| Colonne | Description | Type |
| --- | --- | --- |
| QID | Identifiant Wikidata des entités exclues (écarts > 100 ans uniquement) | `str` |


### 2. Récupération des entités déjà alignées sur Wikidata
  
- Récupération de toutes les entités Wikidata ayant la [propriété "identifiant Musée d'Orsay d'un artiste" (P2268)](https://www.wikidata.org/wiki/Property:P2268) avec une [requête SPARQL](https://query.wikidata.org/#SELECT%20%3FQid%20%3FConstituentID%0AWHERE%20%7B%0A%20%20%3FQid%20wdt%3AP2268%20%3FConstituentID.%0A%20%20%7D)
- Export des résultats en csv
- RegEx pour enlever les "`http://www.wikidata.org/entity/`" de la colonne QID


### 3. Construction des tables

#### a. Création des CSV de base pour les différentes tables 
Voir le [schéma du script de création des csv de base des tables](./Schemas/construction_tables.png)
[Le script de création des csv de base des tables](./Scripts/construction_des_tables.py)

Fonctionnement :
- **Création de la table TMS** : Agrège les identifiants, noms d'affichage et statuts de validation
- **Extraction des événements TMS** : Traite les dates et lieux de naissance/mort avec normalisation
- **Génération de la table Candidats** : Parse les fichiers JSON pour extraire les métadonnées Wikidata
- **Construction des tables d'événements et lieux candidats** : Filtre et normalise les données temporelles et géographiques
- **Création des relations TMS-Candidats** : Extrait les scores d'alignement depuis la colonne `candidats_scores_wikidata`.
- **Filtrage global** : Applique des exclusions cohérentes sur toutes les tables

| Paramètres globaux | Description | Format/Type |
|---|---|---|
| chemin_csv_tms | Chemin du csv final OpenRefine. | `.csv` |
| chemin_csv_nb_liens_creations | Chemin du csv généré par la [requête sur le serveur PRA](#b-le-nombre-de-liens-à-la-création-par-entité-tms) pour récupérer le nombre de liens à la création pour chaque entité TMS | `.csv` |
| chemin_csv_qid | Chemin du csv indiquant les entités préalablement alignées par la communauté Wikidata généré par [une requête SPARQL](#2-récupération-des-entités-déjà-alignées-sur-wikidata) | `.csv` |
| dossier_json | Chemin du dossier contenant les fichiers JSON [les full dumps des candidats Wikidata](#a1-les-dates) | `/dir` |
| chemin_csv_exclusion | Chemin du csv indiquant les candidats Wikidata à exclure | `.csv` |

Fichiers de sortie correspondant aux différentes données pour chaque tables :
```python
table_TMS.csv
Evenements_TMS.csv
Table_Candidats.csv
filtered_tables\Evenements_Candidats.csv
filtered_tables\Lieux_Candidats.csv
filtered_tables\Relations_TMS_Candidats.csv
```

---
Paramètres par fonction :

**Table TMS**

`recuperation_ID_DisplayName_tms(chemin_csv)`
- **Fonction** : Extrait les identifiants TMS uniques avec leurs noms d'affichage
- **Paramètres** : 
  - `chemin_csv` : Chemin du csv final OpenRefine
- **Retour** : DataFrame avec TMS_ID et DisplayName dédupliqués

`ajout_nb_liens_creation(chemin_csv, df_TMS)`
- **Fonction** : Ajoute le nombre de liens/rôles par entité
- **Paramètres** :
  - `chemin_csv` : Chemin vers le fichier des comptages de liens
  - `df_TMS` : DataFrame TMS existant
- **Retour** : DataFrame TMS enrichi

`ajout_statut_validation_deja_alignes(chemin_csv, df_TMS)`
- **Fonction** : Marque les entités déjà alignées par la communauté
- **Paramètres** :
  - `chemin_csv` : Chemin vers le fichier des alignements existants
  - `df_TMS` : DataFrame TMS existant
- **Retour** : DataFrame TMS avec statut de validation

**Événements TMS**

`nettoyage_et_recup_precision_date(date_str)`
- **Fonction** : Normalise les dates et détermine leur précision Wikidata
- **Paramètres** :
  - `date_str` : Chaîne de date à nettoyer
- **Retour** : Tuple (date normalisée, précision Wikidata)
- **Gestion** :
  - Formats supportés : "YYYY ?", "YYYY", "YYYY-MM", "JJ/MM/YYYY"
  - Précisions : 9 (année), 10 (mois), 11 (jour)

`nettoyage_lieu(lieu_str)`
- **Fonction** : Nettoie les chaînes de lieux
- **Paramètres** :
  - `lieu_str` : Chaîne de lieu à nettoyer
- **Retour** : Lieu nettoyé ou None

`traitement_evenements_tms(chemin_csv_tms)`
- **Fonction** : Traite les événements TMS avec fusion dates/lieux
- **Paramètres** :
  - `chemin_csv_tms` : Chemin vers le fichier CSV TMS
- **Retour** : DataFrame des événements normalisés

**Candidats**

`extraire_donnees_candidats(qid, claims, labels)`
- **Fonction** : Extrait les métadonnées d'un candidat Wikidata
- **Paramètres** :
  - `qid` : Identifiant Wikidata
  - `claims` : Déclarations Wikidata
  - `labels` : Labels multilingues
- **Retour** : Liste de tuples (QID, type, nb_id_externes, label)

`traiter_dossier(dossier_json, chemin_csv_sortie)`
- **Fonction** : Traite un dossier de fichiers JSON Wikidata
- **Paramètres** :
  - `dossier_json` : Chemin vers le dossier JSON
  - `chemin_csv_sortie` : Fichier CSV de sortie
- **Gestion** :
  - Traitement par lots avec rapports de progression
  - Gestion d'erreurs JSON avec compteurs détaillés

**Relations**

`extractions_donnees_matchs(chemin_csv_openrefine)`
- **Fonction** : Extrait les relations TMS-Candidats depuis OpenRefine
- **Paramètres** :
  - `chemin_csv_openrefine` : Fichier CSV avec résultats OpenRefine
- **Retour** : DataFrame des relations avec scores
- **Traitement** :
  - Parsing des structures JSON complexes
  - Correction des formats de clés non standardisés

**Filtrage**

`filtrer_qid_candidats_exclus(chemin_csv_candidats, chemin_csv_exclusion)`
- **Fonction** : Filtre les candidats selon une liste d'exclusion
- **Paramètres** :
  - `chemin_csv_candidats` : CSV des candidats à filtrer
  - `chemin_csv_exclusion` : CSV des QID à exclure
- **Retour** : DataFrame filtré

`filter_csv_by_reference_qid(csv_files, reference_csv, output_dir, verbose)`
- **Fonction** : Filtre plusieurs CSV selon un CSV de référence
- **Paramètres** :
  - `csv_files` : Liste des fichiers CSV à filtrer
  - `reference_csv` : CSV de référence pour les QID valides
  - `output_dir` : Répertoire de sortie (optionnel)
  - `verbose` : Mode verbeux pour les logs
- **Retour** : Dictionnaire des DataFrames filtrés
---

**Normalisation des données**

**Dates**
- **Suppression** des préfixes +/- dans les dates candidats
- **Remplacement** des "00" par "01" dans les dates (YYYY-00-00 → YYYY-01-01)
- **Ajustement** automatique de la précision selon les substitutions
- **Gestion** des formats variables avec validation

**Lieux**
- **Nettoyage** des chaînes avec suppression des espaces
- **Filtrage** des valeurs nulles ou vides
- **Préservation** des labels originaux

**Labels**
- **Priorité** des langues : français > multilingue > anglais > autre
- **Fallback** vers le premier label disponible si aucune priorité

---
**Vérification et suivi des erreurs**

**Traitement JSON**
- **Validation** de la structure des fichiers
- **Compteurs** détaillés des erreurs par type
- **Continuation** du traitement malgré les erreurs individuelles

**Validation des données**
- **Vérification** de l'existence des colonnes requises
- **Conversion** de types avec gestion des erreurs
- **Rapports** de diagnostic complets

**Logs**
- **Niveau** WARNING par défaut
- **Messages** détaillés pour le débogage
- **Statistiques** de traitement en temps réel

#### b. Calcul des flags des données principales pour l'affichage dans l'application

[Script d'ajout des scores par comparaison des données principales](./Scripts/calcul_flag.py) (dates et lieux de vie, nom)

Système de score :

| **Critère** | **Score 1** | **Score 0** | **Score -1** |
|-------------|-------------|-------------|--------------|
| **Dates** | Match trouvé entre au moins une date candidat et une date TMS (selon précision minimale) | Données manquantes pour l'un ou l'autre | Aucun match trouvé |
| **Lieux** | Match exact ou inclusion partielle (un lieu contenu dans l'autre) après normalisation | Données manquantes pour l'un ou l'autre | Aucune correspondance trouvée |
| **Noms** | Correspondance exacte OU mêmes mots dans ordre différent | Distance de Levenshtein ≤ 15% OU données manquantes | Distance de Levenshtein > 15% |

- **Normalisation** : Suppression des accents, conversion en minuscules
- **Précision des dates** : Comparaison selon le niveau le plus bas (siècle=7, décennie=8, année=9, mois=10, jour=11)
- **Score total** : Somme des 5 scores individuels (naissance date + mort date + naissance lieu + mort lieu + nom)
- **Plage du score total** : -5 à +5

| Paramètres | Description |
|---|---|
| chemin_csv_table_tms | Chemin vers `table_TMS.csv` | 
| chemin_csv_table_evenement_tms | Chemin vers `Evenements_TMS.csv`|
| chemin_csv_table_evenement_candidats | Chemin vers `\filtered_tables\Evenements_Candidats.csv`|
| chemin_csv_table_lieux_candidats | Chemin vers `\filtered_tables\Lieux_Candidats.csv`|
| chemin_csv_table_relation_tms_candidats | Chemin vers `\filtered_tables\Relations_TMS_Candidats.csv`|
| chemin_csv_table_candidats | Chemin vers `table_Candidats.csv`|

CSV de sortie `table_relation_tms_candidats_with_flags.csv` : 

| Colonnes | Description | type |
| --- | --- | --- |
| TMS_ID | id d'une entité TMS | `int` |
| QID | qid d'un candidat Wikidata | `str` |
| Score_API | score renvoyé par l'API de réconciliation fr Wikidata sur OpenRefine | `int` |
| score_flag_date_naissance | score de correspondance des dates de naissance TMS-Wikidata | `int` |
| score_flag_date_mort | score de correspondance des dates de mort TMS-Wikidata | `int` |
| score_flag_lieu_naissance | score de correspondance des lieux de naissance TMS-Wikidata | `int` |
| score_flag_lieu_mort | score de correspondance des lieux de mort TMS-Wikidata | `int` |
| score_flag_nom | score de correspondance des lieux de naissance TMS-Wikidata | `int` |
| score_flag | score total de correspondance TMS-Wikidata | `int` |


### 4. Création de la base de l'application dans DBeaver

#### a. Création d'un schéma dédié sur le serveur Postgre du serveur LAB
- Création du schéma `app_alignement` dans la base lab_sdpn
- Création d'un utilisateur dédié à l'application pour lire et éditer le schéma `app_alignement`
  > username : aamo
  
  > password : AETKfS0065U1LAkRHhU7
  
#### b. Création des tables à partir des csv
Voir le [modèle de la base SQL de l'application](./Processus/Schemas/Modèle_base_app_alignement.png)
##### b.1. Import des csv et complétion des tables importées

**Import des csv via l'assistant d'import de DBeaver** :
- Import source : à partir d'un csv
- Input file(s) : sélectionner le csv à importer pour la création d'une table
- Table mapping > Configure : renommage des colonnes si nécessaire, typage des colonnes, Mapping = CREATE, Target = nom de la table créée.

**Liste des csv à importer**
- table_TMS.csv
- table_candidat.csv
- table_relation_tms_candidats_with_flags.csv
- filtered_tables\Lieux_Candidats.csv
- filtered_tables\Evenements_Candidats.csv
- Evenements_TMS.csv

**Créationdes clés primaires lorsqu'elles font parties des colonnes préexistantes** (voir les colonnes `PK` qui ne sont pas en italique dans le [modèle de la base](./Processus/Schemas/Modèle_base_app_alignement.png))

**S'assurer que les cellules importées "vides" soient bien `NULL`** : pour toute colonne importée partiellement vide (table_tms.statut_validation) il arrive que dbeaver importe les cellule vide avec des espaces ou autre à la place de `NULL`.
Requête SQL pour remédier au problème :
```sql
UPDATE [ nom_de_la_table]
SET nom_de_la_colonne = NULL
WHERE TRIM(nom_de_la_colonne ) = '';
```


---

**Complétion des tables importées** : créer les colonnes manquantes "vides" en typant (voir les colonnes en *italique* dans le [modèle de la base](./Processus/Schemas/Modèle_base_app_alignement.png))

**Créationdes clés primaires auto-incrémentées :**
- evenements_candidat.id_evenement
- evenements_tms.id_evenement
- lieux_candidats.id_lieu
- table_candidat.id_candidat
- relations_tms_candidats.id_match

Requête SQL de création des colonnes auto-incrémentées :
```sql
ALTER TABLE [nom_de_la_table]
ADD COLUMN [nom_de_la_colonne] bigint GENERATED BY DEFAULT AS IDENTITY;
```
Puis ajouter les contraintes `PRIMARY KEY`.


##### b.2. Création des tables utilisateur et historique
Création des tables "vides" : utilisateurs et historique (voir les tables en *italique* dans le [modèle de la base](./Processus/Schemas/Modèle_base_app_alignement.png))
- Script SQL table utilisateurs :
  ```sql
  CREATE TABLE app_alignement.utilisateurs (
    email varchar(320) NOT NULL,
    mdp text NOT NULL,
    date_heure_creation timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    id_utilisateur int8 GENERATED ALWAYS AS IDENTITY( MINVALUE 0 NO MAXVALUE START 0 NO CYCLE) NOT NULL,
    preferences json DEFAULT '["tous"]'::json NULL,
    CONSTRAINT utilisateurs_pkey PRIMARY KEY (id_utilisateur)
  );
  ```
- Script SQL table historique :
  ```sql
  CREATE TABLE app_alignement.historique (
    id_utilisateur int4 NULL,
    id_match int4 NULL,
    date_heure_action timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    "action" varchar(20) NOT NULL,
    id_historique int8 GENERATED ALWAYS AS IDENTITY( MINVALUE 0 NO MAXVALUE START 0 NO CYCLE) NOT NULL,
    CONSTRAINT historique_pkey PRIMARY KEY (id_historique)
  );
  ```

##### b.3. Rajouter les contraintes de clés étrangères
| Colonne d'origine de la clé | Colonnes faisant référence à la clé |
|---|---|
| table_tms.tms_id | evenements_tms.tms_id ; relations_tms_candidats.tms_id |
| table_candidats.qid | evenements_candidats.qid ; lieux_candidats.qid ; relations_tms_candidats |
| relations_tms_candidats.id_match | historique.id_match |
| utilisateurs.id_utilisateur | historique.id_utilisateur |

## III. Création d'une table des données TMS pour l'affichage dans l'application
**Pourquoi une table en dehors de la base principale ?**

  Permet de faciliter l'appel des données (évite les requêtes complexes dans le code de l'application et gain en rapidité d'affichage). Permet aussi de pouvoir suivre l'état de la donnée TMS au moment de l'alignement et de garder une trace de tout changement potentiel.

  Spécificités de la table :
  - nom : `tms-constituent_constituent-description`
  - schema : `main`
  - droits de lecture pour l'utilisateur aamo ([voir création de l'utilisateur](#a-création-dun-schéma-dédié-sur-le-serveur-postgre-du-serveur-lab))
  - [modèle de la table](./Processus/Schemas/Modèle_table_%20tms-constituent_constituent-description.png)
  - Agrégation des champs multivalués : colonnes type JSON
  - colonne `db_update` : TIMESTAMP de la dernière mise à jour des données de l'entité

## IV. Inscription des alignements sur Wikidata

   Voir partie basse du [schema du processus](./Schemas/schema_global_processus_alignement.png) d'alignement. 
   
  ### 1. Personnes et Institutions alignées et publiées sur le répertoire des artistes et personnalités
  Pour inscrire les alignements des entités TMS vers un/des candidat.s Wikidata sur Wikidata il faut ajouter la propriété [P2268](https://www.wikidata.org/wiki/Property:P2268) (identifiant Musée d'Orsay d'un artiste ou d'une personnalité) avec pour valeur l'ID TMS (`Constituents.ConstituentID`). La propriété fait référence directement au répertoire des artistes et personnalités publié par l'EPMO en reconstituant l'URL (https://www.musee-orsay.fr/fr/ressources/repertoire-artistes-personnalites/[id tms]). Il faut alors s'assurer, pour pouvoir ajouter la propriété P2268, que les TMS alignées y sont bien publiées. 

  #### a. Récupération des ids TMS avec le `statut_validation` "aligne" et du ou des candidats validés (une ligne par paire TMS-candidat distincte)
     
   Requête à réaliser sur le serveur Postgre du serveur LAB, base lab_sdpn, schema app_alignement (base principale de l'application)

   ```sql
    select rtc.tms_id, rtc.qid
    from app_alignement.relations_tms_candidats rtc 
    inner join app_alignement.table_tms tt on tt.tms_id = rtc.tms_id
    inner join app_alignement.historique h on h.id_match = rtc.id_match
    where tt.statut_validation = 'aligne'
    and h.action = 'valide';
   ``` 
   Exporter le résultat en csv

  #### b. Récupération des ids TMS publiés sur le répertoire 
     
   Requête à réaliser sur le serveur PRA

   ```sql
    SELECT DISTINCT ufx.ID
    FROM UserFieldXrefs ufx
    WHERE ufx.ContextID = 40
      AND TRY_CAST(FieldValue AS int) IS NOT NULL
      AND TRY_CAST(FieldValue AS int) != 0;
   ```

   Exporter le résultat en csv

  #### c. Exclusion des ids TMS non publiés sur le répertoire et fromatagepour Quickstatements
     
   Voir [script dédié](./Scripts/exclusion_formattage_quickstatements.py)

   Voir exemple de [fichier_sortie](./quickstatements_p2268_20250731_110138.txt)

   Voir exemple de [script_sql_statut_publie](./script_sql_statut_publie_20250731_110138.sql)
     

   | Paramètres | Description | Format/Type |
   | --- | --- | --- |
   | ids_alignes_candidats | Nom du fichier résultant de l'export du schéma app_alignement | `.csv` |
   | ids_repertoire | Nom du fichier résultant de l'export du serveur PRA | `.csv` |
   | fichier_sortie | Nom du fichier txt de sortie préformaté pour Quickstatements ( qid [TAB] P2268 [TAB] tms_id ). Le nom contient un horodatage de sa création pour tracer les différentes édition sur Wikidata. | `.txt` |
   | script_sql_statut_publie | Nom du fichier sql contenant la requête de mise à jour du `statut_validation` des entités TMS concernée par l'édition sur Wikidata Le nom contient un horodatage de sa création pour tracer les différentes édition sur Wikidata. | `.sql` | 


  #### d. Inscription via Quickstatements
     
   Depuis [l'interface de Quickstatements](https://quickstatements.toolforge.org/index_old.html) (ici, l'ancienne version car je n'avais pas de compte Wikidata agréé): 
   - Se connecter avec un compte Wikidata valide (50 modifications et 4 jours d'ancienneté)
   - Importer des commandes > format version 1
   - Copier-coller le contenu du fichier de sortie après exclusion des entités non publiées et formatage dans l'interface de saisie.
   - Lancer l'édition de masse.
  
   >Note : il est aussi possible de le faire depuis un csv avec en-tête.

   >Note : le service est parfois instable ce qui provoque des erreurs. Il est possible de relancer plusieurs fois le processus jusqu'à ce qu'il n'y est plus d'erreurs.

   >Note : il serait préférable de pouvoir utiliser la [V2 de Quickstatements](https://quickstatements.toolforge.org/#/user) (actuelle) avec un compte agréé. Cette dernière fonctionne de la même manière (voir [Aide:Quickstatements](https://www.wikidata.org/wiki/Help:QuickStatements/fr)).

   >Note : la v2 possède une API utilisable en script (génération d'un token et specs dans l'onglet utilisateur une fois connecté). Il serait envisageable sur le long terme, de créer un script automatisant l'exclusion des entités non publiées, le formatage et l'édition de masse.

  #### e. Mise à jour du statut_validation des entités TMS concernées
     
   Executer le [script SQL](./script_sql_statut_publie_20250731_110138.sql) généré par le script d'exclusion et de formatage pour Quickstatements sur le schéma app_alignement, base lab_sdnp, serveur Postgre du serveur LAB. 

### 2. Personnes et institutions non-alignées et publiées sur le répertoire des artistes et personnalités

   Les entités TMS peuvent obtenir un `statut_validation` = 'non_aligne' pour deux raisons : 
   - L'API de réconciliation Wikidata FR, utilisée via OpenRefine, n'a pas trouvé de candidat
   - Un utilisateur de 2AMO a refusé tous les candidats possibles pour l'entité TMS en question
   
   De ce fait, il est alors envisageable de créer un nouvel élément Wikidata pour renseigner cette entité TMS. Cela implique la définition de règles pour décider de la création de ces éléments ou non. Ces règles pourraient porter sur les thématiques suivantes :
   - La quantité minimale de données sur l'entité TMS (dates de vie, lieux de vie, occupation etc.)
   - La qualité minimale des données (exactitude des renseignements etc.)
   - L'utilité de l'entité en interne (nombre de liens à la création, ancien personnel scientifique, rareté d'information sur le web etc.)

   Il faudra aussi décider des propriétés à renseigner, en plus de la [P2268](https://www.wikidata.org/wiki/Property:P2268). Pour cela, il est possible de se référer au [mapping](./Mapping_TMS_wikidata.xlsx) des champs TMS vers Wikidata. Lorsque les champs ne sont pas colorés, cela signifie simplement que les propriétés n'ont pas été utilisées pour le [processus de réconciliation avec l'API](#2-projet-openrefine).

### 3. Personnes et institutions non publiées dans le répertoire des artistes et personnalités

  #### a. Les entités TMS alignées
     
   Dans le cas d'une entité TMS alignée mais non publiée sur le répertoire, il est envisageable d'exploiter l'information pour des usages internes. Le numéro Wikidata pourrait être ajouté dans la table `AltNum` (dédiée aux autres identifiants) afin de donner accès à l'URL Wikidata au personnel scientifique du musée. 

  #### b. Les entités TMS non alignées
     
   Dans le cas ou l'entité n'est ni alignée, ni publiée dans le répertoire, l'information de la non existence d'un élément Wikidata correspondant reste enregistrée sur la base principale de l'application (`statut validation` = 'non_aligne').
  
## V. Import de nouvelles entités TMS dans la base de 2AMO

  Pour importer de nouvelles entités TMS dans la base de l'application, il faudra reproduire les étapes d'extraction des données du PRA, du projet OpenRefine, de la récupération des données des candidats, de l'exclusion des candidats par écarts de dates, du calcul des scores_flag_* et intégrer les données dans les tables correspondantes.

## LISTE DES SCRIPTS ET DOCUMENTS CITES
### Scripts
1. Script de sélection d'entités TMS au hasard et génération de la requête SQL pour extraction des données du PRA ([script](./Scripts/sample_maker_v2.py)) ([en savoir plus](#1-extraction-des-données-depuis-le-serveur-pra-avec-des-requêtes-sql))
2. Script de récupération des lignes avec erreurs à partir de l'export csv OpenRefine ([script](./Scripts/recup_batch_error.py)) ([en savoir plus](./Scripts/recup_batch_error.py))
3. Script de fusion des différents exports Openrefine sans erreur ([script](./Scripts/fusion_batch_error_et_premier_batch.py)) ([en savoir plus](#2-projet-openrefine))
4. Script de téléchargement des données des candidats ([script](./Scripts/recuperation_json_asynchrone_candidats.py)) ([en savoir plus](#a-récuperation-des-données-wikidata-pour-chaque-candidat))
5. Script d'extraction des dates des candidats ([script](./Scripts/Extraction_dates_from_full_dumps.py)) ([en savoir plus](#a1-les-dates))
6. Script de téléchargement des labels et rangs des lieux de naissance et de mort ([script](./Scripts/recuperation_json_lieux_only_batchs_sparql.py)) ([en savoir plus](#a2-les-lieux))
7. Script d'extraction des labels et rangs des lieux de naissance et de mort ([script](./Scripts/Extraction_lieux_et_rang_from_batch_sparql.py)) ([en savoir plus](#a2-les-lieux))
8. Script de création des csv de base des tables ([script](./Scripts/construction_des_tables.py)) ([en savoir plus](#3-construction-des-tables))
9. Script d'ajout des scores de comparaison des données principales ([script](./Scripts/calcul_flag.py)) ([en savoir plus](#b-calcul-des-flags-des-données-principales-pour-laffichage-dans-lapplication))
10. Script d'exclusion des entites TMS non publiées sur le répertoire, formatage des données pour Quickstatements et génération du .sql de mise à jour des `statut_validation` ([script](./Scripts/exclusion_formattage_quickstatements.py)) ([en savoir plus](#1-personnes-et-institutions-alignées-et-publiées-sur-le-répertoire-des-artistes-et-personnalités))

### Documents
1. Schema global du processus d'Alignement ([voir le document](./Schemas/schema_global_processus_alignement.png))
1. Dossier Projet openrefine ([voir le document](./Projet_OpenRefine)) ([en savoir plus](#2-projet-openrefine))
2. Mapping ([voir le document](./Mapping_TMS_wikidata.xlsx))
3. Specs de l'API de réconciliation Wikidata ([voir le document](https://www.w3.org/community/reports/reconciliation/CG-FINAL-specs-0.2-20230410/))
4. Notes sur le fonctionnement de l'API de réconciliation wikidata ([voir le document](../Notes_et_observations/propriétés_api_reconciliation.docx))
5. Aperçu de l'export final OpenRefine ([voir le document](alignements_sans_error_complet.csv))
6. Modèle de la base SQL de l'application : app_alignement ([voir le document](./Processus/Schemas/Modèle_base_app_alignement.png)) ([en savoir plus](#ii-construction-de-la-base-principale-postgre-pour-lapplication))
7. Modèle de la table `tms-constituent_constituent-description` ([voir le document](./Processus/Schemas/Modèle_table_%20tms-constituent_constituent-description.png)) ([en savoir plus](#iii-création-dune-table-des-données-tms-pour-laffichage-dans-lapplication))
8. Exemple de fichier de sortie formatté pour Quickstatements ([voir document](./quickstatements_p2268_20250731_110138.txt)) ([en savoir plus](#1-personnes-et-institutions-alignées-et-publiées-sur-le-répertoire-des-artistes-et-personnalités))
9. Exemple de script SQL pour la mise à jour des `statut_validation` après edition des entites wikdiata alignees ([voir document](./script_sql_statut_publie_20250731_110138.sql)) ([en savoir plus](#1-personnes-et-institutions-alignées-et-publiées-sur-le-répertoire-des-artistes-et-personnalités))
10. Page d'aide FR de Quickstatements ([voir le document](https://www.wikidata.org/wiki/Help:QuickStatements/fr))