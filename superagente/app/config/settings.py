import os
from dotenv import load_dotenv

load_dotenv()

PVE_URL = os.environ.get("PVE_URL", "")
PVE_TOKEN_ID = os.environ.get("PVE_TOKEN_ID", "")
PVE_TOKEN_SECRET = os.environ.get("PVE_TOKEN_SECRET", "")
PVE_VERIFY_SSL = os.environ.get("PVE_VERIFY_SSL", "false").lower() == "true"

PROXMOX_ENABLED = bool(PVE_URL and PVE_TOKEN_ID and PVE_TOKEN_SECRET)
