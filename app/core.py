import requests
import os
import json
import csv
import yaml
import logging
from datetime import datetime
import pymysql

# Configuration API
CLIENT_ID = os.getenv("WCL_CLIENT_ID", "[VOTRE_WCL_CLIENT_ID]")
CLIENT_SECRET = os.getenv("WCL_CLIENT_SECRET", "[VOTRE_WCL_CLIENT_SECRET]")

# Configuration DB (via variables d'environnement pour Docker)
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_USER = os.getenv("DB_USER", "scrapper")
DB_PASS = os.getenv("DB_PASSWORD", "[VOTRE_MOT_DE_PASSE_SCRAPPER]")
DB_NAME = os.getenv("DB_NAME", "datamart-wow")

# Mappings
DIFFICULTY_MAP = {"normal": 3, "heroic": 4, "mythic": 5}
REGION_MAP = {"Europe": "eu", "United States": "us"}

# Logger
logger = logging.getLogger("WCLScrapper")

def setup_logging():
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def get_access_token():
    response = requests.post(
        "https://www.warcraftlogs.com/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    if response.status_code != 200:
        raise Exception(f"Auth Error: {response.text}")
    return response.json()["access_token"]

def make_api_request(token, query, variables):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "https://www.warcraftlogs.com/api/v2/client",
        json={"query": query, "variables": variables},
        headers=headers
    )
    if response.status_code != 200:
        raise Exception(f"API Error: {response.text}")
    return response.json()

def load_hero_map():
    try:
        # Chercher dans le même dossier que ce fichier core.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "hero_talents_map.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

HERO_ID_MAP = load_hero_map()

def get_hero_spec_from_talents(talents_list):
    for t in talents_list:
        tid = str(t.get("talentID"))
        if tid in HERO_ID_MAP:
            return HERO_ID_MAP[tid]
    return None

def fetch_rankings(token, encounter_id, difficulty, region):
    all_players = []
    page = 1
    
    while len(all_players) < 500:
        query = """
        query($encounterID: Int!, $difficulty: Int!, $serverRegion: String!, $page: Int!) {
            worldData {
                encounter(id: $encounterID) {
                    characterRankings(
                        difficulty: $difficulty,
                        serverRegion: $serverRegion,
                        page: $page,
                        includeCombatantInfo: true
                    )
                }
            }
        }
        """
        variables = {
            "encounterID": encounter_id,
            "difficulty": difficulty,
            "serverRegion": region,
            "page": page
        }
        
        data = make_api_request(token, query, variables)
        rankings = data.get("data", {}).get("worldData", {}).get("encounter", {}).get("characterRankings", {}).get("rankings", [])
        
        if not rankings:
            break
            
        for rank_data in rankings:
            if len(all_players) >= 500: break
            
            # Extraction des données simplifiées
            talents = []
            raw_talents = rank_data.get("talents", [])
            for t in raw_talents:
                if t.get("talentID"):
                    t_data = {"talentID": t.get("talentID")}
                    if "name" in t: t_data["name"] = t["name"]
                    talents.append(t_data)
            
            hero_spec = get_hero_spec_from_talents(talents)
            
            # Gear extraction (Trinkets)
            gear = rank_data.get("gear", [])
            trinket_1, trinket_2 = None, None
            if len(gear) > 12 and gear[12]: trinket_1 = gear[12].get("name")
            if len(gear) > 13 and gear[13]: trinket_2 = gear[13].get("name")

            # Flat dictionary for CSV
            player = {
                "rank": len(all_players) + 1,
                "name": rank_data.get("name"),
                "class": rank_data.get("class"),
                "spec": rank_data.get("spec"),
                "hero_spec": hero_spec,
                "amount": rank_data.get("amount"),
                "duration": rank_data.get("duration"),
                "ilvl": rank_data.get("bracketData"),
                "server": rank_data.get("server", {}).get("name") if isinstance(rank_data.get("server"), dict) else rank_data.get("server"),
                "guild": rank_data.get("guild", {}).get("name") if isinstance(rank_data.get("guild"), dict) else rank_data.get("guild"),
                "trinket_1": trinket_1,
                "trinket_2": trinket_2,
                "report": rank_data.get("report", {}).get("code"),
                "fight_id": rank_data.get("report", {}).get("fightID")
            }
            all_players.append(player)
        
        page += 1
        
    return all_players

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def init_db():
    # Tente d'initialiser la table si elle n'existe pas
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Lire le fichier SQL local
            base_dir = os.path.dirname(os.path.abspath(__file__))
            sql_path = os.path.join(base_dir, "init_db.sql")
            if os.path.exists(sql_path):
                with open(sql_path, "r") as f:
                    sql = f.read()
                cursor.execute(sql)
                logger.info("Database initialized (table checked).")
        conn.close()
    except Exception as e:
        logger.error(f"DB Init Error: {e}")

def save_to_db(players, raid, boss, difficulty, region):
    if not players:
        return

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Nettoyer les anciennes données pour ce boss/diff/region pour éviter les doublons lors des re-run ?
            # Pour l'instant on ajoute juste (append only), on gérera le nettoyage plus tard si besoin.
            
            sql = """
                INSERT INTO player_rankings 
                (raid, boss, difficulty, region, player_rank, player_name, guild_name, 
                 class, spec, hero_spec, amount, duration, ilvl, 
                 trinket_1_name, trinket_2_name, report_code, fight_id, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = []
            now = datetime.now()
            
            for p in players:
                values.append((
                    raid, boss, difficulty, region,
                    p["rank"], p["name"], p["guild"],
                    p["class"], p["spec"], p["hero_spec"],
                    p["amount"], p["duration"], p["ilvl"],
                    p["trinket_1"], p["trinket_2"],
                    p["report"], p["fight_id"],
                    now
                ))
            
            cursor.executemany(sql, values)
            logger.info(f"    DB: Inserted {len(players)} rows.")
            
        conn.close()
    except Exception as e:
        logger.error(f"DB Error: {e}")

def sanitize(name):
    return name.replace(" ", "_").replace("'", "").replace(",", "")

def run_scraper_for_raid(target_raid_key, target_difficulty=None):
    setup_logging()
    
    # Déterminer le dossier de base pour la sortie (là où se trouve le script exécuté)
    import sys
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Load config (remonter d'un cran car on sera dans un sous-dossier)
    # On cherche le fichier raid_id.yaml dans le dossier parent du script exécuté
    # ou dans le dossier courant si on lance depuis la racine
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "raid_id.yaml")
    
    if not os.path.exists(config_path):
        # Fallback pour exécution locale
        config_path = "raid_id.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    if target_raid_key not in config:
        logger.error(f"Raid key '{target_raid_key}' not found in configuration.")
        return

    raid_config = config[target_raid_key]
    raid_name = raid_config["name"]
    raid_id = raid_config["id"]
    
    # Init DB structure
    init_db()
    
    logger.info(f"=== Scraping Raid: {raid_name} ===")
    if target_difficulty:
        logger.info(f"=== Mode: {target_difficulty.upper()} only ===")
    
    try:
        token = get_access_token()
    except Exception as e:
        logger.error(e)
        return

    # Get encounters
    query = """query($id: Int!) { worldData { zone(id: $id) { encounters { id name } } } }"""
    data = make_api_request(token, query, {"id": raid_id})
    encounters = data.get("data", {}).get("worldData", {}).get("zone", {}).get("encounters", [])
    
    for region_name, _ in raid_config["regions"].items():
        region_code = REGION_MAP.get(region_name, "eu")
        
        for diff_name, _ in raid_config["difficulty"].items():
            # Filter if a specific difficulty is requested
            if target_difficulty and diff_name.lower() != target_difficulty.lower():
                continue

            diff_id = DIFFICULTY_MAP.get(diff_name, 5)
            
            logger.info(f"Processing {region_name} / {diff_name}")
            
            for boss in encounters:
                boss_name = boss["name"]
                logger.info(f"  > Boss: {boss_name}")
                
                players = fetch_rankings(token, boss["id"], diff_id, region_code)
                
                # 1. Save to DB
                save_to_db(players, raid_name, boss_name, diff_name, region_name)
                
                # 2. Save to CSV (Backup)
                path = os.path.join(
                    script_dir,
                    sanitize(diff_name),
                    sanitize(region_name),
                    f"{sanitize(boss_name)}.csv"
                )
                # save_csv(players, path) # Uncomment if you want CSVs too
                # logger.info(f"    Saved {len(players)} rows to {path}")

if __name__ == "__main__":
    print("This module is intended to be imported.")
