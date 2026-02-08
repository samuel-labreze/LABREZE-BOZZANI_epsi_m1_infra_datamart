# Modele Conceptuel de Donnees (MCD)

## Vue d'ensemble

Le modele de donnees du projet WoW Mythic Analytics est concu pour analyser les performances des joueurs en raid mythique.

## Entites

### RAID
Represente un raid (instance) de World of Warcraft.

| Attribut | Type | Description |
|----------|------|-------------|
| raid_id | INT (PK) | Identifiant unique |
| name | VARCHAR(100) | Nom du raid |
| zone_id | INT | ID WarcraftLogs |
| expansion | VARCHAR(50) | Extension du jeu |

### BOSS
Represente un boss dans un raid.

| Attribut | Type | Description |
|----------|------|-------------|
| boss_id | INT (PK) | Identifiant unique |
| name | VARCHAR(100) | Nom du boss |
| raid_id | INT (FK) | Reference au raid |
| encounter_id | INT | ID WarcraftLogs |

### CLASS
Represente une classe jouable.

| Attribut | Type | Description |
|----------|------|-------------|
| class_id | INT (PK) | Identifiant unique |
| name | VARCHAR(50) | Nom de la classe |
| slug | VARCHAR(50) | Identifiant texte |

### SPEC
Represente une specialisation de classe.

| Attribut | Type | Description |
|----------|------|-------------|
| spec_id | INT (PK) | Identifiant unique |
| name | VARCHAR(50) | Nom de la spec |
| class_id | INT (FK) | Reference a la classe |
| role | ENUM | DPS/Healer/Tank |

### HERO_SPEC
Represente un hero talent (TWW).

| Attribut | Type | Description |
|----------|------|-------------|
| hero_id | INT (PK) | Identifiant unique |
| name | VARCHAR(50) | Nom du hero talent |
| spec_id | INT (FK) | Reference a la spec |

### REGION
Represente une region geographique.

| Attribut | Type | Description |
|----------|------|-------------|
| region_id | INT (PK) | Identifiant unique |
| name | VARCHAR(50) | EU / US |
| code | INT | 1=US, 2=EU |

### TRINKET
Represente un trinket (bijou).

| Attribut | Type | Description |
|----------|------|-------------|
| trinket_id | INT (PK) | Identifiant unique |
| name | VARCHAR(255) | Nom du trinket |
| item_id | INT | ID Blizzard |

### PLAYER_RANKING (Fait)
Table de faits centrale.

| Attribut | Type | Description |
|----------|------|-------------|
| id | INT (PK) | Identifiant unique |
| boss_id | INT (FK) | Reference au boss |
| region_id | INT (FK) | Reference a la region |
| class_id | INT (FK) | Reference a la classe |
| spec_id | INT (FK) | Reference a la spec |
| hero_spec_id | INT (FK) | Reference au hero talent |
| trinket_1_id | INT (FK) | Reference trinket 1 |
| trinket_2_id | INT (FK) | Reference trinket 2 |
| player_name | VARCHAR(100) | Nom du joueur |
| guild_name | VARCHAR(100) | Nom de la guilde |
| player_rank | INT | Rang dans le classement |
| amount | DOUBLE | DPS/HPS |
| duration | INT | Duree du combat (s) |
| ilvl | INT | Item level |
| scraped_at | DATETIME | Date de collecte |

## Relations

```
RAID (1) ──────────< (N) BOSS
CLASS (1) ─────────< (N) SPEC
SPEC (1) ──────────< (N) HERO_SPEC
BOSS (1) ──────────< (N) PLAYER_RANKING
REGION (1) ────────< (N) PLAYER_RANKING
CLASS (1) ─────────< (N) PLAYER_RANKING
SPEC (1) ──────────< (N) PLAYER_RANKING
HERO_SPEC (1) ─────< (N) PLAYER_RANKING
TRINKET (1) ───────< (N) PLAYER_RANKING (x2)
```

## Implementation actuelle

Pour des raisons de performance et de simplicite, nous utilisons une table denormalisee `player_rankings` qui combine toutes les dimensions en une seule table.

Cette approche est courante en BI pour les data marts car elle :
- Simplifie les requetes analytiques
- Evite les jointures couteuses
- Facilite l'exposition des metriques via SQL Exporter

Le schema normalise ci-dessus represente le modele conceptuel ideal, tandis que l'implementation reelle utilise un modele en etoile aplati.
