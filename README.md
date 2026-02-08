# World of Warcraft - Mythic Raid Performance Analytics

## Projet Entrepots de données / Datamart - EPSI M1 INFRA Campus Bordeaux

Entrepot de donnees decisionnel pour l'analyse des performances des meilleurs joueurs de World of Warcraft en contenu Mythique.

---

## Equipe

| Prenom | Nom | Role |
|--------|-----|------|
| Samuel | LABREZE | Etudiant / Joueur Mythique WoW / Nerd qui pu |

---

## Source de donnees

**API WarcraftLogs GraphQL v2**
https://www.warcraftlogs.com/api/v2/client

WarcraftLogs est la plateforme de reference pour le suivi des performances en raid dans World of Warcraft. Elle collecte et agrege les logs de combat de millions de joueurs a travers le monde.

### Donnees extraites

| Donnee | Description |
|--------|-------------|
| **Raids** | Nerub-ar Palace, Liberation of Undermine, Manaforge Omega |
| **Difficulte** | Mythique uniquement (niveau de difficulte le plus eleve) |
| **Echantillon** | Top 500 joueurs EU + Top 500 joueurs US par boss |
| **Metriques** | DPS, duree de combat, item level, classe, specialisation, hero talents, trinkets |

**Volume** : ~72 000 entrees (24 boss x 500 joueurs x 2 regions x 3 raids)

---

## Objectif metier

> **Identifier la meilleure classe a jouer (avec le bon hero talent et les bons trinkets) pour performer au mieux sur chaque boss Mythique, selon le role.**

### Questions analytiques

- Quelles classes/specs dominent le top 10 par boss ?
- Quels trinkets sont les plus utilises par les meilleurs joueurs ?
- Y a-t-il des differences significatives entre EU et US ?
- Quel est le DPS moyen par classe/spec/hero talent ?
- Quelles sont les guildes les plus representees dans les rankings ?

---

## Architecture technique

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ARCHITECTURE ELT                                 │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  WarcraftLogs    │
    │  GraphQL API v2  │
    └────────┬─────────┘
             │ OAuth 2.0
             ▼
    ┌──────────────────┐
    │  Python Scripts  │  ◄── EXTRACT : Authentification + Requetes GraphQL
    │  (app/core.py)   │      TRANSFORM : Enrichissement hero talents
    │  (run_all.py)    │      LOAD : Insertion MariaDB
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │     MariaDB      │  ◄── Stockage relationnel
    │  player_rankings │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   SQL Exporter   │  ◄── Exposition metriques Prometheus
    │   (30+ metrics)  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │    Prometheus    │  ◄── Collecte et stockage time-series
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │     Grafana      │  ◄── Visualisation et dashboards
    │   (4 dashboards) │
    └──────────────────┘
```

---

## Pipeline de transformation des donnees

Bien que n'utilisant pas Airbyte, dbt ou Jupyter, notre pipeline Python realise les memes operations de transformation :

### 1. Extraction (Extract)

```python
# app/core.py - get_access_token()
# Authentification OAuth 2.0 aupres de WarcraftLogs
response = requests.post(
    "https://www.warcraftlogs.com/oauth/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    data={"grant_type": "client_credentials"}
)
```

### 2. Transformation (Transform)

```python
# app/core.py - fetch_rankings() + get_hero_spec_from_talents()

# Transformation 1 : Extraction des donnees imbriquees GraphQL
# La reponse JSON est aplatie en structure tabulaire

# Transformation 2 : Resolution des hero talents
# Les talent_id bruts sont mappes vers des noms lisibles
# via hero_talents_map.json (466 mappings)

# Transformation 3 : Enrichissement
# - Extraction des trinkets depuis combatantInfo
# - Calcul des metriques derivees
# - Normalisation des noms de classes/specs
```

### 3. Chargement (Load)

```python
# app/core.py - save_to_db()
# Insertion en batch dans MariaDB avec gestion des doublons
cursor.executemany("""
    INSERT INTO player_rankings
    (raid, boss, difficulty, region, player_rank, ...)
    VALUES (%s, %s, %s, ...)
""", batch_data)
```

### 4. Exposition (Serve)

```yaml
# sql-exporter/sql_exporter.yml
# 30+ requetes SQL transforment les donnees brutes
# en metriques Prometheus agregees
```

---

## Modele de donnees

### Schema de la table principale

```sql
CREATE TABLE player_rankings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Dimensions contextuelles
    raid VARCHAR(100) NOT NULL,
    boss VARCHAR(100) NOT NULL,
    difficulty VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,

    -- Dimensions joueur
    player_rank INT NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    guild_name VARCHAR(100),
    class VARCHAR(50) NOT NULL,
    spec VARCHAR(50) NOT NULL,
    hero_spec VARCHAR(50),

    -- Metriques de performance
    amount DOUBLE NOT NULL,          -- DPS
    duration INT NOT NULL,           -- Duree en secondes
    ilvl INT,                        -- Item level

    -- Equipement
    trinket_1_name VARCHAR(255),
    trinket_2_name VARCHAR(255),

    -- Tracabilite
    report_code VARCHAR(50),
    fight_id INT,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Index pour performances
    INDEX idx_raid_boss (raid, boss),
    INDEX idx_class_spec (class, spec, hero_spec)
);
```

### Modele conceptuel (MCD)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MODELE CONCEPTUEL                                 │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │    RAID      │         │     BOSS     │         │   REGION     │
    ├──────────────┤         ├──────────────┤         ├──────────────┤
    │ raid_id (PK) │◄───┐    │ boss_id (PK) │    ┌───►│ region_id(PK)│
    │ name         │    │    │ name         │    │    │ name         │
    │ zone_id      │    │    │ raid_id (FK) │────┘    └──────────────┘
    └──────────────┘    │    └──────────────┘                 │
                        │           │                         │
                        │           ▼                         │
                        │    ┌──────────────────────────────┐ │
                        └────│      PLAYER_RANKING          │◄┘
                             ├──────────────────────────────┤
                             │ id (PK)                      │
    ┌──────────────┐         │ raid_id (FK)                 │
    │    CLASS     │         │ boss_id (FK)                 │
    ├──────────────┤         │ region_id (FK)               │
    │ class_id (PK)│◄────────│ class_id (FK)                │
    │ name         │         │ spec_id (FK)                 │
    └──────────────┘         │ hero_spec_id (FK)            │
           │                 │ player_name                  │
           ▼                 │ guild_name                   │
    ┌──────────────┐         │ player_rank                  │
    │    SPEC      │         │ amount (DPS)                 │
    ├──────────────┤         │ duration                     │
    │ spec_id (PK) │◄────────│ ilvl                         │
    │ name         │         │ trinket_1 (FK)               │
    │ class_id(FK) │         │ trinket_2 (FK)               │
    │ role         │         │ scraped_at                   │
    └──────────────┘         └──────────────────────────────┘
           │                              │
           ▼                              │
    ┌──────────────┐                      │
    │  HERO_SPEC   │                      │
    ├──────────────┤         ┌────────────┴─────────────┐
    │ hero_id (PK) │◄────────│        TRINKET           │
    │ name         │         ├──────────────────────────┤
    │ spec_id (FK) │         │ trinket_id (PK)          │
    └──────────────┘         │ name                     │
                             │ item_level               │
                             └──────────────────────────┘
```

> **Note** : Pour des raisons de performance et de simplicite d'implementation, nous avons opte pour un modele denomalise (flat table) qui combine toutes les dimensions. Cette approche est courante en Business Intelligence pour les data marts analytiques.

---

## Metriques exposees (SQL Exporter)

### Statistiques globales
- `wow_total_players_scraped` - Nombre total de joueurs
- `wow_players_by_region` - Joueurs par region
- `wow_players_by_raid` - Joueurs par raid

### Performance par classe/spec
- `wow_avg_dps_class` - DPS moyen par classe
- `wow_max_dps_class` - DPS max par classe
- `wow_avg_dps_spec` - DPS moyen par specialisation
- `wow_avg_dps_hero_spec` - DPS moyen par hero spec

### Presence dans le top
- `wow_top10_presence` - Classes dans le top 10
- `wow_top10_presence_spec` - Specs dans le top 10
- `wow_top10_hero_spec_presence` - Hero specs dans le top 10

### Trinkets
- `wow_trinket_usage` - Trinkets les plus utilises
- `wow_trinket_combo_popularity` - Combinaisons populaires
- `wow_trinket_by_boss` - Trinkets par boss

### Analyse par boss
- `wow_boss_avg_dps` - DPS moyen par boss
- `wow_boss_avg_duration` - Duree moyenne par boss
- `wow_best_spec_per_boss` - Meilleure spec par boss

### Guildes
- `wow_top_guilds_presence` - Guildes les plus representees
- `wow_guild_top10_presence` - Guildes dans le top 10

---

## Dashboards Grafana

### 1. Dashboard Global (`grafana-dashboard-wow-v3.json`)
Vue d'ensemble de tous les raids avec comparaisons globales.

### 2. Nerub-ar Palace (`grafana-dashboard-nerub-ar-palace.json`)
Analyse detaillee du raid Nerub-ar Palace (8 boss).

### 3. Liberation of Undermine (`grafana-dashboard-liberation-of-undermine.json`)
Analyse detaillee du raid Liberation of Undermine (8 boss).

### 4. Manaforge Omega (`grafana-dashboard-manaforge-omega.json`)
Analyse detaillee du raid Manaforge Omega (8 boss).

---

## Captures d'ecran

### Dashboard Global
![Dashboard Global](screenshots/dashboard_global.png)

### Nerub-ar Palace
![Nerub-ar Palace](screenshots/dashboard_nerub_ar.png)

### Liberation of Undermine
![Liberation of Undermine](screenshots/dashboard_liberation.png)

### Manaforge Omega
![Manaforge Omega](screenshots/dashboard_manaforge.png)

---

## Deploiement

### Prerequis
- Docker & Docker Compose
- Acces reseau aux services (MariaDB, Prometheus)

### Lancement

```bash
# Cloner le depot
git clone <url-du-depot>
cd rendu_tp

# Lancer la stack complete
docker-compose up -d

# Verifier les services
docker-compose ps

# Lancer un scraping manuel
docker-compose exec scraper python run_all.py
```

### Acces aux services

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| SQL Exporter | http://localhost:9399/metrics | - |

---

## Structure du projet

```
rendu_tp/
├── README.md                    # Ce fichier
├── docker-compose.yml           # Orchestration des services
├── app/
│   ├── Dockerfile               # Image Docker des scripts
│   ├── requirements.txt         # Dependances Python
│   ├── core.py                  # Bibliotheque principale (OAuth, API, DB)
│   ├── run_all.py               # Orchestrateur multi-thread
│   ├── check_quota.py           # Verification quota API
│   ├── wipe_db.py               # Nettoyage base de donnees
│   ├── init_db.sql              # Schema de la table
│   ├── raid_id.yaml             # Configuration des raids
│   └── hero_talents_map.json    # Mapping des hero talents
├── sql-exporter/
│   ├── docker-compose.yml       # (legacy)
│   └── sql_exporter.yml         # Configuration des metriques
├── grafana/
│   ├── dashboards/              # Fichiers JSON des dashboards
│   └── provisioning/            # Auto-provisioning Grafana
├── screenshots/                 # Captures d'ecran des dashboards
└── docs/
    └── schema_mcd.md            # Documentation du modele
```

---

## Justification des choix techniques

### Pourquoi Python plutot qu'Airbyte/dbt ?

1. **Flexibilite API GraphQL** : L'API WarcraftLogs utilise GraphQL avec pagination complexe et authentification OAuth. Python permet un controle fin de ces mecanismes.

2. **Transformation en temps reel** : Les hero talents necessitent un mapping dynamique depuis un fichier JSON de 466 entrees. Cette logique est plus naturelle en Python.

3. **Multi-threading** : Le scraping de 48 endpoints (24 boss x 2 regions) beneficie du parallelisme Python (8 workers).

### Pourquoi Grafana plutot que Metabase ?

1. **Integration Prometheus native** : Grafana est l'outil de reference pour visualiser des metriques Prometheus.

2. **Dashboards as Code** : Les dashboards JSON sont versionnables et reproductibles.

3. **Richesse des visualisations** : Bar charts, pie charts, tables avec gauges, heatmaps.

---

## Resultats et conclusions

Le pipeline permet d'identifier :

- Les **classes meta** pour chaque boss mythique
- Les **hero talents optimaux** par specialisation
- Les **trinkets BiS** (Best in Slot) par contexte
- Les **differences regionales** EU vs US
- Les **guildes dominantes** dans le competitive

Ces insights sont directement exploitables par les joueurs souhaitant optimiser leurs performances en raid mythique.

---

## Licence

Projet academique - EPSI 2026

Donnees issues de WarcraftLogs (https://www.warcraftlogs.com) - Usage educatif uniquement.

