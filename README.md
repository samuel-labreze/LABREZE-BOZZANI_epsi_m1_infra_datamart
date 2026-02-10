# World of Warcraft - Mythic Raid Performance Analytics

## Projet Entrepots de données / Datamart - EPSI M1 INFRA Campus Bordeaux

Entrepot de donnees decisionnel pour l'analyse des performances des meilleurs joueurs de World of Warcraft en contenu Mythique.

---

## Equipe

| Prenom | Nom | Role |
|--------|-----|------|
| Samuel | LABREZE | Etudiant / Joueur Mythique WoW|
| Arman | BOZZANI | Etudiant / Ancien joueur de WoW|

---

# ════════════════════════════════
# ÉTAPE 1 - JEU DE DONNÉES
# ════════════════════════════════

## Source de donnees

**API WarcraftLogs GraphQL v2**
- **Lien** : https://www.warcraftlogs.com/api/v2/client
- **Documentation** : https://www.warcraftlogs.com/v2-api-docs/warcraft/

WarcraftLogs est la plateforme de reference pour le suivi des performances en raid dans World of Warcraft. Elle collecte et agrege les logs de combat de millions de joueurs a travers le monde.

### Caracteristiques du jeu de donnees

| Critere | Valeur |
|---------|--------|
| **Volume** | ~72 000 entrees (24 boss x 500 joueurs x 2 regions x 3 raids) |
| **Type de donnees** | Statistiques in-game detaillees |
| **Jeu** | World of Warcraft (MMORPG avec fortes interactions) |

### Donnees extraites

| Donnee | Description |
|--------|-------------|
| **Raids** | Nerub-ar Palace, Liberation of Undermine, Manaforge Omega |
| **Difficulte** | Mythique uniquement (niveau de difficulte le plus eleve) |
| **Echantillon** | Top 500 joueurs EU + Top 500 joueurs US par boss |
| **Metriques** | DPS, duree de combat, item level, classe, specialisation, hero talents, trinkets |

### Objectif metier

> **Identifier la meilleure classe a jouer (avec le bon hero talent et les bons trinkets) pour performer au mieux sur chaque boss Mythique, selon le role.**

#### Questions analytiques

- Quelles classes/specs dominent le top 10 par boss ?
- Quels trinkets sont les plus utilises par les meilleurs joueurs ?
- Y a-t-il des differences significatives entre EU et US ?
- Quel est le DPS moyen par classe/spec/hero talent ?
- Quelles sont les guildes les plus representees dans les rankings ?

---

# ════════════════════════════════
# ÉTAPE 2 - ARCHITECTURE TECHNIQUE (Docker Compose ELT)
# ════════════════════════════════

## Architecture ELT

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
    │  Python Scraper  │  ◄── EXTRACT : Authentification + Requetes GraphQL
    │  (app/core.py)   │      TRANSFORM : Enrichissement hero talents
    │  (run_all.py)    │      LOAD : Insertion MariaDB
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │     MariaDB      │  ◄── Stockage relationnel (Extract/Load)
    │  player_rankings │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   SQL Exporter   │  ◄── Transformation SQL (30+ metriques)
    │   (30+ metrics)  │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │    Prometheus    │  ◄── Collecte time-series
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │     Grafana      │  ◄── Visualisation (4 dashboards)
    │   (4 dashboards) │
    └──────────────────┘
```

## Docker Compose - Services

| Service | Image | Port | Role |
|---------|-------|------|------|
| **mariadb** | mariadb:10.11 | 3306 | Base de donnees relationnelle |
| **scraper** | python:3.11-slim | - | Scripts ETL Python |
| **sql-exporter** | burningalchemist/sql_exporter | 9399 | Transformation SQL → Prometheus |
| **prometheus** | prom/prometheus | 9090 | Stockage time-series |
| **grafana** | grafana/grafana | 3000 | Visualisation |

## Pipeline de donnees

### Extract (Extraction)

```python
# app/core.py - get_access_token()
# Authentification OAuth 2.0 aupres de WarcraftLogs
response = requests.post(
    "https://www.warcraftlogs.com/oauth/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    data={"grant_type": "client_credentials"}
)
```

### Transform (Transformation)

```python
# app/core.py - fetch_rankings() + get_hero_spec_from_talents()

# Transformation 1 : Extraction des donnees imbriquees GraphQL
# La reponse JSON est aplatie en structure tabulaire

# Transformation 2 : Resolution des hero talents
# Les talent_id bruts sont mappes vers des noms lisibles
# via hero_talents_map.json (466 mappings)

# Transformation 3 : Enrichissement
# - Extraction des trinkets depuis combatantInfo
# - Normalisation des noms de classes/specs
```

### Load (Chargement)

```python
# app/core.py - save_to_db()
# Insertion en batch dans MariaDB
cursor.executemany("""
    INSERT INTO player_rankings
    (raid, boss, difficulty, region, player_rank, ...)
    VALUES (%s, %s, %s, ...)
""", batch_data)
```

### Serve (Exposition via SQL Exporter)

```yaml
# sql-exporter/sql_exporter.yml
# 30+ requetes SQL transforment les donnees brutes
# en metriques Prometheus agregees
```

---

# ════════════════════════════════
# ÉTAPE 3 - MODÈLE RELATIONNEL (ERD / MCD)
# ════════════════════════════════

## Modele Conceptuel de Donnees (MCD)

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

# ════════════════════════════════
# ÉTAPE 3.5 - MODÈLE DIMENSIONNELLE
# ════════════════════════════════

# 🌟 Modèle Dimensionnel en Étoile — WoW Player Rankings

## Description

Ce document présente la modélisation dimensionnelle en étoile (Star Schema) pour un entrepôt de données (Data Warehouse) dédié au classement des joueurs World of Warcraft par boss de raid.

---

## Schéma en Étoile

```
════════════════════════════════════════════════════════════
MODÈLE DIMENSIONNEL EN ÉTOILE (STAR SCHEMA)
════════════════════════════════════════════════════════════

                            ┌──────────────────────┐
                            │      DIM_RAID         │
                            ├──────────────────────┤
                            │ raid_id (PK)          │
                            │ raid_name             │
                            │ zone                  │
                            └──────────┬───────────┘
                                       │
    ┌──────────────────────┐           │           ┌──────────────────────┐
    │     DIM_PLAYER       │           │           │      DIM_BOSS        │
    ├──────────────────────┤           │           ├──────────────────────┤
    │ player_id (PK)       │           │           │ boss_id (PK)         │
    │ player_name          │           │           │ boss_name            │
    │ guild_name           │           │           │ raid_name            │
    └──────────┬───────────┘           │           └──────────┬───────────┘
               │                       │                      │
               │    ┌──────────────────┴──────────────────┐   │
               │    │          FAIT_RANKING                │   │
               │    ├─────────────────────────────────────┤   │
               │    │ ranking_id (PK)                     │   │
               ├───►│                                     │◄──┤
               │    │ ── Clés étrangères ──               │   │
               │    │ raid_id (FK)        ────────────────┼───┘
               │    │ boss_id (FK)        ────────────────┘
               │    │ region_id (FK)      ─────────────────────┐
               │    │ spec_id (FK)        ──────────┐          │
               └────┤ player_id (FK)                │          │
                    │ trinket_1_id (FK)   ──────┐   │          │
                    │ trinket_2_id (FK)   ──────┤   │          │
                    │                           │   │          │
                    │ ── Mesures ──             │   │          │
                    │ player_rank               │   │          │
                    │ dps_amount                │   │          │
                    │ duration                  │   │          │
                    │ ilvl                      │   │          │
                    │ scraped_at                │   │          │
                    └───────────────────────────┘   │          │
                         │          │               │          │
                         │          │               │          │
    ┌────────────────────┘          │               │          └──────────────────────┐
    │                               │               │                                 │
    ▼                               │               ▼                                 ▼
┌──────────────────────┐            │    ┌──────────────────────┐       ┌──────────────────────┐
│     DIM_TRINKET      │            │    │      DIM_SPEC        │       │     DIM_REGION       │
├──────────────────────┤            │    ├──────────────────────┤       ├──────────────────────┤
│ trinket_id (PK)      │            │    │ spec_id (PK)         │       │ region_id (PK)       │
│ trinket_name         │            │    │ class_name           │       │ region_name          │
│ item_level           │            │    │ spec_name            │       └──────────────────────┘
└──────────────────────┘            │    │ hero_spec_name       │
  ▲ trinket_1 & trinket_2          │    │ role                 │
                                    │    └──────────────────────┘
                                    │      ▲ dénormalisée :
                                    │        CLASS + SPEC + HERO_SPEC
                                    │
                                    └── (liens FK)
```

---

## Tables

### Table de faits

| Table | Grain | Description |
|-------|-------|-------------|
| **FAIT_RANKING** | 1 ligne par performance joueur/boss | Stocke les métriques de classement DPS pour chaque encounter |

#### Mesures

| Colonne | Type | Description |
|---------|------|-------------|
| `player_rank` | INT | Rang du joueur sur le boss |
| `dps_amount` | FLOAT | DPS réalisé |
| `duration` | INT | Durée du combat (secondes) |
| `ilvl` | INT | Niveau d'équipement du joueur |
| `scraped_at` | TIMESTAMP | Date/heure du scraping |

#### Clés étrangères

| FK | Dimension cible |
|----|-----------------|
| `raid_id` | DIM_RAID |
| `boss_id` | DIM_BOSS |
| `region_id` | DIM_REGION |
| `spec_id` | DIM_SPEC |
| `player_id` | DIM_PLAYER |
| `trinket_1_id` | DIM_TRINKET |
| `trinket_2_id` | DIM_TRINKET |

---

### Tables de dimensions

| Dimension | PK | Attributs | Description |
|-----------|----|-----------|-------------|
| **DIM_RAID** | `raid_id` | raid_name, zone | Instance de raid |
| **DIM_BOSS** | `boss_id` | boss_name, raid_name | Boss d'un raid |
| **DIM_REGION** | `region_id` | region_name | Région serveur (EU, US, etc.) |
| **DIM_SPEC** | `spec_id` | class_name, spec_name, hero_spec_name, role | Spécialisation joueur (dénormalisée) |
| **DIM_PLAYER** | `player_id` | player_name, guild_name | Joueur et sa guilde |
| **DIM_TRINKET** | `trinket_id` | trinket_name, item_level | Bijou équipé |

---

## Notes de modélisation

- **DIM_SPEC dénormalisée** : fusionne les tables `CLASS`, `SPEC` et `HERO_SPEC` du modèle relationnel en une seule dimension plate (principe du Star Schema — pas de flocon/snowflake)
- **Role-playing dimension** : `DIM_TRINKET` est référencée deux fois par la table de faits via `trinket_1_id` et `trinket_2_id`
- **DIM_PLAYER** : extraite pour isoler les attributs descriptifs du joueur (nom, guilde) des mesures de performance
- **Grain** : une ligne = une performance d'un joueur sur un boss spécifique, à un moment donné (`scraped_at`)

## Modele Conceptuel de Donnees (MCD)

## Schema physique (Implementation)

> **Note** : Pour des raisons de performance et de simplicite, nous avons opte pour un modele **denormalise** (flat table). Cette approche est courante en Business Intelligence pour les data marts analytiques.

```sql
-- app/init_db.sql
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

---

# ════════════════════════════════
# ÉTAPE 4 - CHARGEMENT & TRANSFORMATION DES DONNÉES
# ════════════════════════════════

## Transformations effectuees

### 1. Extraction API → Donnees brutes

Le scraper Python (`run_all.py`) effectue :
- **Authentification OAuth 2.0** avec WarcraftLogs
- **Requetes GraphQL paginées** (500 joueurs max par boss)
- **8 workers parallèles** pour optimiser le temps de scraping

### 2. Transformations Python

| Transformation | Description | Fichier |
|----------------|-------------|---------|
| **Aplatissement JSON** | Structure GraphQL imbriquee → table plate | `core.py` |
| **Resolution Hero Talents** | talent_id → nom lisible (466 mappings) | `hero_talents_map.json` |
| **Extraction Trinkets** | combatantInfo.gear[12,13] → noms | `core.py` |
| **Normalisation** | Classes/specs en format standard | `core.py` |

### 3. Transformations SQL (SQL Exporter)

30+ requetes SQL transforment les donnees brutes en metriques agregees :

```yaml
# sql-exporter/sql_exporter.yml - Exemples

# DPS moyen par classe et region
SELECT class, region, ROUND(AVG(amount), 0) as avg_dps
FROM player_rankings
WHERE scraped_at > NOW() - INTERVAL 24 HOUR
GROUP BY class, region

# Trinkets les plus populaires
SELECT trinket, SUM(cnt) as count FROM (
    SELECT trinket_1_name as trinket, COUNT(*) as cnt
    FROM player_rankings GROUP BY trinket_1_name
    UNION ALL
    SELECT trinket_2_name as trinket, COUNT(*) as cnt
    FROM player_rankings GROUP BY trinket_2_name
) combined
GROUP BY trinket ORDER BY count DESC LIMIT 20
```

### 4. Metriques exposees (30+)

| Categorie | Metriques |
|-----------|-----------|
| **Stats globales** | `wow_total_players_scraped`, `wow_players_by_region`, `wow_players_by_raid` |
| **Performance classe** | `wow_avg_dps_class`, `wow_max_dps_class`, `wow_avg_dps_spec` |
| **Top 10** | `wow_top10_presence`, `wow_top10_presence_spec`, `wow_top10_hero_spec_presence` |
| **Trinkets** | `wow_trinket_usage`, `wow_trinket_combo_popularity`, `wow_trinket_by_boss` |
| **Boss** | `wow_boss_avg_dps`, `wow_boss_avg_duration`, `wow_best_spec_per_boss` |
| **Guildes** | `wow_top_guilds_presence`, `wow_guild_top10_presence` |

---

# ════════════════════════════════
# VISUALISATION (Grafana)
# ════════════════════════════════

## Dashboards Grafana

| Dashboard | Fichier | Description |
|-----------|---------|-------------|
| **Global** | `grafana-dashboard-wow-v3.json` | Vue d'ensemble tous raids |
| **Nerub-ar Palace** | `grafana-dashboard-nerub-ar-palace.json` | Analyse raid (8 boss) |
| **Liberation of Undermine** | `grafana-dashboard-liberation-of-undermine.json` | Analyse raid (8 boss) |
| **Manaforge Omega** | `grafana-dashboard-manaforge-omega.json` | Analyse raid (8 boss) |

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

# ════════════════════════════════
# DÉPLOIEMENT
# ════════════════════════════════

## Prerequis

- Docker & Docker Compose
- Credentials WarcraftLogs API (CLIENT_ID, CLIENT_SECRET)

## Installation

```bash
# 1. Cloner le depot
git clone https://github.com/samuel-labreze/LABREZE_epsi_m1_infra_datamart.git
cd LABREZE_epsi_m1_infra_datamart

# 2. Configurer les credentials
# Editer docker-compose.yml et remplacer les placeholders :
# - [VOTRE_MOT_DE_PASSE_ROOT]
# - [VOTRE_MOT_DE_PASSE_SCRAPPER]
# - [VOTRE_WCL_CLIENT_ID]
# - [VOTRE_WCL_CLIENT_SECRET]

# 3. Lancer la stack
docker-compose up -d

# 4. Verifier les services
docker-compose ps

# 5. Voir les logs du scraper
docker logs -f wow-scraper
```

## Acces aux services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **SQL Exporter** | http://localhost:9399/metrics | - |
| **MariaDB** | localhost:3306 | root / [votre_password] |

---

## Structure du projet

```
rendu_tp/
├── README.md                    # Documentation (ce fichier)
├── docker-compose.yml           # Orchestration Docker
├── .env.example                 # Template variables d'environnement
│
├── app/                         # Scripts Python (ETL)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── core.py                  # Bibliotheque principale
│   ├── run_all.py               # Orchestrateur multi-thread
│   ├── init_db.sql              # Schema SQL
│   ├── raid_id.yaml             # Config raids
│   └── hero_talents_map.json    # Mapping talents
│
├── sql-exporter/                # Transformation SQL
│   └── sql_exporter.yml         # 30+ metriques
│
├── prometheus/                  # Collecte metriques
│   └── prometheus.yml
│
├── grafana/                     # Visualisation
│   ├── dashboards/              # 4 fichiers JSON
│   └── provisioning/            # Auto-config
│
├── screenshots/                 # Captures dashboards
│   ├── dashboard_global.png
│   ├── dashboard_nerub_ar.png
│   ├── dashboard_liberation.png
│   └── dashboard_manaforge.png
│
└── docs/
    └── schema_mcd.md            # Documentation modele
```

---

## Justification des choix techniques

### Pourquoi Python plutot qu'Airbyte/dbt ?

1. **API GraphQL complexe** : Pagination, OAuth, donnees imbriquees
2. **Transformation temps reel** : Mapping hero talents (466 entrees)
3. **Multi-threading** : 8 workers pour 48 endpoints

### Pourquoi Grafana plutot que Metabase ?

1. **Integration Prometheus native**
2. **Dashboards as Code** (JSON versionnable)
3. **Richesse visualisations** : Bar charts, pie charts, gauges

---

## Licence

Projet academique - EPSI 2026

Donnees issues de WarcraftLogs (https://www.warcraftlogs.com) - Usage educatif uniquement.





