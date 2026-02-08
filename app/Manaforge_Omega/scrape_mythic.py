import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import run_scraper_for_raid

if __name__ == "__main__":
    run_scraper_for_raid("manaforge_omega", "mythic")
