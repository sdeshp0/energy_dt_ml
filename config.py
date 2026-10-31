"""
All the site settings in one place, so the scripts agree with each other.
Change things here, not inside the scripts.
"""
import os
from pathlib import Path

# ---- where things live ----
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"          # downloaded / generated data (not in git)
IMG_DIR = ROOT / "notes" / "images"

# ---- the site ----
SITE_NAME = "Fresno food processing plant (made up)"
LATITUDE = 36.74
LONGITUDE = -119.79
YEAR = 2025

# Everything is stored in local *standard* time (UTC-8, no daylight saving),
# because that's what NSRDB gives back by default. CAISO data gets converted
# to match. See the experiment log for why this matters.
TIMEZONE = "Etc/GMT+8"   # yes, the sign is backwards in this naming scheme

# ---- demand (loadcast) ----
ANNUAL_MWH = 10_000
ELEC_SHARE = 0.20
HEAT_TO_COLD = 7.4
PROCESS_CLASS = "semi_continuous"
CARRIER_CORRELATION = 0.75

# ---- grid ----
# DLAP_PGAE is the price PG&E-area load pays in the CAISO market. Fresno is
# in PG&E territory. TH_ZP26_GEN-APND (the Path 26 trading hub) is a backup.
CAISO_PRICE_NODE = "DLAP_PGAE-APND"

# ---- keys (put them in a .env file, see .env.example) ----
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

NREL_API_KEY = os.environ.get("NREL_API_KEY", "")
NREL_EMAIL = os.environ.get("NREL_EMAIL", "")

DATA_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)
