import requests
import os
import time
import sys

# Allow overriding for local testing or docker
POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
PB_ADMIN_EMAIL = os.environ.get("PB_ADMIN_EMAIL", "admin@hukukburosu.com")
PB_ADMIN_PASSWORD = os.environ.get("PB_ADMIN_PASSWORD", "AvukatRota2026!")

def get_admin_token():
    url = f"{POCKETBASE_URL}/api/admins/auth-with-password"
    payload = {
        "identity": PB_ADMIN_EMAIL,
        "password": PB_ADMIN_PASSWORD
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("token")
        else:
            print(f"Admin auth failed: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"Connection error to {url}: {e}")
        return None

def create_collection(token, schema_def):
    headers = {"Authorization": token}

    # Check if exists
    try:
        check_url = f"{POCKETBASE_URL}/api/collections/{schema_def['name']}"
        resp = requests.get(check_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            print(f"Collection '{schema_def['name']}' already exists.")
            return True
    except Exception as e:
        print(f"Error checking collection: {e}")
        return False

    url = f"{POCKETBASE_URL}/api/collections"
    resp = requests.post(url, json=schema_def, headers=headers, timeout=10)

    if resp.status_code == 200:
        print(f"Collection '{schema_def['name']}' created successfully.")
        return True
    else:
        print(f"Failed to create collection '{schema_def['name']}': {resp.text}")
        return False

def init_pocketbase():
    print(f"Initializing PocketBase at {POCKETBASE_URL}...")

    token = None
    # Retry loop to wait for PocketBase to be ready
    for i in range(30):
        token = get_admin_token()
        if token:
            break
        print(f"Waiting for PocketBase... ({i+1}/30)")
        time.sleep(2)

    if not token:
        print("Could not authenticate with PocketBase after retries. Exiting init.")
        return

    # 1. Cases (Dosyalar)
    cases_schema = {
        "name": "cases",
        "type": "base",
        "schema": [
            {
                "name": "case_no",
                "type": "text",
                "required": True,
                "options": {"min": 1, "max": None, "pattern": ""}
            },
            {
                "name": "client",
                "type": "text",
                "required": False,
                "options": {}
            }, # Müvekkil
            {
                "name": "opponent",
                "type": "text",
                "required": False,
                "options": {}
            }, # Karşı Taraf
            {
                "name": "city",
                "type": "text",
                "required": True,
                "options": {}
            }, # Şehir
            {
                "name": "district",
                "type": "text",
                "required": False,
                "options": {}
            }, # İlçe
            {
                "name": "court_office",
                "type": "text",
                "required": False,
                "options": {}
            }, # Mahkeme/Daire
            {
                "name": "case_type",
                "type": "select",
                "required": False,
                "options": {
                    "maxSelect": 1,
                    "values": ["Hukuk Davası", "Ceza Davası", "İdari Dava", "Tüketici Davası", "Ticaret Davası", "İcra Takibi"]
                }
            },
            {
                "name": "status",
                "type": "select",
                "required": False,
                "options": {
                    "maxSelect": 1,
                    "values": ["Aktif", "Duruşma Bekliyor", "Keşif", "Bilirkişi", "Kapandı"]
                }
            },
            {
                "name": "priority",
                "type": "select",
                "required": False,
                "options": {
                    "maxSelect": 1,
                    "values": ["Normal", "Acil", "Kritik"]
                }
            },
            {
                "name": "follower_lawyer",
                "type": "text",
                "required": False,
                "options": {}
            }, # Takipçi Avukat
            {
                "name": "authorized_lawyer",
                "type": "text",
                "required": False,
                "options": {}
            }, # Yetkili Avukat
            {
                "name": "due_date",
                "type": "date",
                "required": False,
                "options": {}
            }, # Son İşlem / Duruşma Tarihi
            {
                "name": "description",
                "type": "text",
                "required": False,
                "options": {}
            },
            {
                "name": "lat",
                "type": "number",
                "required": False,
                "options": {}
            },
            {
                "name": "lon",
                "type": "number",
                "required": False,
                "options": {}
            },
        ]
    }

    create_collection(token, cases_schema)

if __name__ == "__main__":
    init_pocketbase()
