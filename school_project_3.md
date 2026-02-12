# Atelier 3 - Visualisation

*atelier3-infra.md 2026-02-03*

Pour cette dernière séance, vous exposez les données traitées via un outil de Business Intelligence et validez la stabilité de votre infrastructure.

## Étape 1 - Déploiement de l'outil de BI

Intégrer l'outil de visualisation (Notebook, Metabase, Apache Superset, ...) à votre architecture de conteneur :

* Connecter l'outil directement à la base de données de l'entrepôt (Data Warehouse).
* S'assurer que le service de BI démarre correctement via le `docker-compose`.

## Étape 2 - Indicateurs (KPIs)

Définir au moins 5 indicateurs clés de performance avec au moins 2 indicateurs de chaque type :

* **Agrégation simple**, ex : Taux de victoire, durée moyenne des parties, nombre de joueurs actifs, ...
* **Mesures croisées**, ex : Évolution du score moyen en fonction de l'expérience, distribution des choix de personnages, ...
* Les mesures croisées doivent être représentées par un graphique pertinent (Bar chart, Line chart, Heatmap, ...).

## Étape 3 - Centralisation des logs

Mettre en place un service pour collecter les logs de tous vos conteneurs (DB, ELT, BI) en un seul point.

* Ajouter un service de gestion de logs au `docker-compose` de type **Dozzle** pour une interface légère (ou une stack Loki/Grafana très simplifiée).
* Configurer les conteneurs pour que leurs flux de sortie (stdout/stderr) soient consultables depuis cette interface unique.
* Recréer et documenter une erreur type (ex: échec de connexion à la DB) vue à travers cet outil dans le readme.

## Étape 4 - Documentation

Documenter dans le `README` :

* Les prérequis d'installation
* La procédure de lancement complet de la stack
* Les valeurs configurables
* Les points de vigilance pour l'ajout de service