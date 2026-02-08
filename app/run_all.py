import os
import sys
import time
import yaml
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Dossier de base (là où se trouve ce script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from core import (
    get_access_token,
    make_api_request,
    fetch_rankings,
    save_to_db,
    init_db,
    DIFFICULTY_MAP,
    REGION_MAP
)

# Configuration
MAX_WORKERS = 8  # Nombre de threads parallèles
TARGET_DIFFICULTY = "mythic"

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("MultiScrapper")


def load_config():
    """Charge la configuration des raids depuis raid_id.yaml"""
    config_path = os.path.join(BASE_DIR, "raid_id.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_all_encounters(token, config):
    """Récupère tous les boss de tous les raids configurés"""
    all_encounters = []

    for raid_key, raid_config in config.items():
        raid_id = raid_config["id"]
        raid_name = raid_config["name"]

        query = """query($id: Int!) { worldData { zone(id: $id) { encounters { id name } } } }"""
        data = make_api_request(token, query, {"id": raid_id})
        encounters = data.get("data", {}).get("worldData", {}).get("zone", {}).get("encounters", [])

        for encounter in encounters:
            all_encounters.append({
                "raid_key": raid_key,
                "raid_name": raid_name,
                "boss_id": encounter["id"],
                "boss_name": encounter["name"]
            })

    return all_encounters


def create_scrape_jobs(encounters, config):
    """Crée la liste des jobs à exécuter (boss × région)"""
    jobs = []

    for encounter in encounters:
        raid_config = config[encounter["raid_key"]]

        for region_name in raid_config["regions"].keys():
            region_code = REGION_MAP.get(region_name, "eu")
            diff_id = DIFFICULTY_MAP.get(TARGET_DIFFICULTY, 5)

            jobs.append({
                "raid_name": encounter["raid_name"],
                "boss_id": encounter["boss_id"],
                "boss_name": encounter["boss_name"],
                "difficulty": TARGET_DIFFICULTY,
                "diff_id": diff_id,
                "region_name": region_name,
                "region_code": region_code
            })

    return jobs


def scrape_boss(token, job):
    """Scrappe un boss spécifique (exécuté dans un thread)"""
    try:
        players = fetch_rankings(
            token,
            job["boss_id"],
            job["diff_id"],
            job["region_code"]
        )

        save_to_db(
            players,
            job["raid_name"],
            job["boss_name"],
            job["difficulty"],
            job["region_name"]
        )

        return {
            "success": True,
            "job": job,
            "count": len(players)
        }
    except Exception as e:
        return {
            "success": False,
            "job": job,
            "error": str(e)
        }


def main():
    print("=" * 60)
    print("   SCRAPING MULTITHREAD - MYTHIC ONLY")
    print("=" * 60)

    start_time = time.time()

    # Initialiser la DB
    init_db()

    # Charger la config
    config = load_config()
    logger.info(f"Configuration chargée: {len(config)} raids")

    # Obtenir le token OAuth
    try:
        token = get_access_token()
        logger.info("Token OAuth obtenu")
    except Exception as e:
        logger.error(f"Erreur d'authentification: {e}")
        return

    # Récupérer tous les encounters
    encounters = get_all_encounters(token, config)
    logger.info(f"Boss trouvés: {len(encounters)}")

    # Créer les jobs (boss × région)
    jobs = create_scrape_jobs(encounters, config)
    logger.info(f"Jobs à exécuter: {len(jobs)} (boss × région)")

    print("-" * 60)
    print(f"Lancement de {len(jobs)} tâches avec {MAX_WORKERS} workers...")
    print("-" * 60)

    # Exécuter en parallèle
    success_count = 0
    error_count = 0
    total_players = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="Scraper") as executor:
        # Soumettre tous les jobs
        futures = {
            executor.submit(scrape_boss, token, job): job
            for job in jobs
        }

        # Traiter les résultats au fur et à mesure
        for future in as_completed(futures):
            result = future.result()
            job = result["job"]

            if result["success"]:
                success_count += 1
                total_players += result["count"]
                logger.info(
                    f"✓ {job['raid_name']} / {job['boss_name']} / {job['region_name']} "
                    f"- {result['count']} joueurs"
                )
            else:
                error_count += 1
                logger.error(
                    f"✗ {job['raid_name']} / {job['boss_name']} / {job['region_name']} "
                    f"- Erreur: {result['error']}"
                )

    # Résumé
    duration = time.time() - start_time
    print("=" * 60)
    print(f"SCRAPING TERMINÉ en {duration:.1f} secondes")
    print(f"  Succès: {success_count}/{len(jobs)}")
    print(f"  Erreurs: {error_count}")
    print(f"  Total joueurs insérés: {total_players}")
    print("=" * 60)


if __name__ == "__main__":
    main()
