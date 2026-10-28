import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Guruh egalari yoki bot super-adminlari ID ro'yxati (vergul bilan ajratilgan)
raw_owners = os.getenv("OWNER_IDS", "")
OWNER_IDS = [int(x.strip()) for x in raw_owners.split(",") if x.strip().isdigit()]

# Standart ban limiti (admin shunchadan ko'p ban bersa tushiriladi)
BAN_LIMIT = int(os.getenv("BAN_LIMIT", 25))

# Banlar hisoblanadigan vaqt oralig'i (soatda)
TIME_WINDOW_HOURS = int(os.getenv("TIME_WINDOW_HOURS", 24))

# Ma'lumotlar bazasi fayli
DB_PATH = BASE_DIR / "mafia_guard.db"
