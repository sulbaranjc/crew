import requests
from app.config.settings import PVE_URL, PVE_TOKEN_ID, PVE_TOKEN_SECRET, PVE_VERIFY_SSL


class ProxmoxAPI:
    def __init__(self):
        self.base_url = PVE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.verify = PVE_VERIFY_SSL
        self.session.headers.update({
            "Authorization": f"PVEAPIToken={PVE_TOKEN_ID}={PVE_TOKEN_SECRET}"
        })

    def get(self, path: str) -> dict:
        if not path.startswith("/"):
            path = "/" + path
        r = self.session.get(f"{self.base_url}{path}", timeout=15)
        r.raise_for_status()
        return r.json()

    def version(self): return self.get("/api2/json/version")
    def nodes(self): return self.get("/api2/json/nodes")
    def cluster_status(self): return self.get("/api2/json/cluster/status")
    def cluster_resources(self): return self.get("/api2/json/cluster/resources")
