import os
import requests

class ProxmoxAPI:
    def __init__(self):
        self.base_url = os.environ["PVE_URL"].rstrip("/")
        self.token_id = os.environ["PVE_TOKEN_ID"]
        self.token_secret = os.environ["PVE_TOKEN_SECRET"]
        self.session = requests.Session()
        self.session.verify = os.environ.get("PVE_VERIFY_SSL", "true").lower() == "true"
        self.session.headers.update({
            "Authorization": f"PVEAPIToken={self.token_id}={self.token_secret}"
        })

    def get(self, path: str) -> dict:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        r = self.session.get(url, timeout=15)
        r.raise_for_status()
        return r.json()

    def version(self): return self.get("/api2/json/version")
    def nodes(self): return self.get("/api2/json/nodes")
    def cluster_status(self): return self.get("/api2/json/cluster/status")
    def cluster_resources(self): return self.get("/api2/json/cluster/resources")
