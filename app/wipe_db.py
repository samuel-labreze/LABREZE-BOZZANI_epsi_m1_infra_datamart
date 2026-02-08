import pymysql
import sys

# Configuration DB (identique à core.py)
DB_HOST = "bdd.epsi.lsnetwork.int"
DB_USER = "scrapper"
DB_PASS = "TGByhn123!"
DB_NAME = "datamart-wow"


def wipe_database():
    print("=" * 50)
    print("   WIPE DATABASE - player_rankings")
    print("=" * 50)

    # Connexion
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"Erreur de connexion: {e}")
        sys.exit(1)

    # Afficher le nombre de lignes avant
    cursor.execute("SELECT COUNT(*) FROM player_rankings")
    count = cursor.fetchone()[0]
    print(f"Lignes actuelles: {count}")

    if count == 0:
        print("La table est déjà vide.")
        conn.close()
        return

    # Confirmation
    response = input(f"\nSupprimer {count} lignes ? (oui/non): ")

    if response.lower() != "oui":
        print("Annulé.")
        conn.close()
        return

    # Wipe
    cursor.execute("TRUNCATE TABLE player_rankings")
    conn.commit()

    print("\nTable player_rankings vidée.")
    print("=" * 50)

    conn.close()


if __name__ == "__main__":
    wipe_database()
