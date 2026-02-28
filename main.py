import json
import requests
from datetime import datetime

API_URL = "https://openrouter.ai/api/v1/models"
SNAPSHOT_FILE = "snapshot.json"


def fetch_models():
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()
    return response.json()["data"]


def extract_prices(models):
    return [
        {
            "id": model["id"],
            "name": model.get("name", ""),
            "provider": model["id"].split("/")[0] if "/" in model["id"] else "unknown",
            "price_per_1k_input": model.get("pricing", {}).get("prompt", 0),
            "price_per_1k_output": model.get("pricing", {}).get("completion", 0),
            "updated_at": model.get("updated_at", ""),
        }
        for model in models
    ]


def load_snapshot():
    try:
        with open(SNAPSHOT_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_snapshot(data):
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_price_changes(current, previous):
    changes = []
    prev_by_id = {m["id"]: m for m in previous}
    for model in current:
        prev = prev_by_id.get(model["id"])
        if prev:
            if model["price_per_1k_input"] != prev["price_per_1k_input"]:
                changes.append({
                    "model": model["id"],
                    "type": "input",
                    "old": prev["price_per_1k_input"],
                    "new": model["price_per_1k_input"],
                })
            if model["price_per_1k_output"] != prev["price_per_1k_output"]:
                changes.append({
                    "model": model["id"],
                    "type": "output",
                    "old": prev["price_per_1k_output"],
                    "new": model["price_per_1k_output"],
                })
    return changes


def main():
    print(f"[{datetime.now().isoformat()}] Fetching models...")
    models = fetch_models()
    prices = extract_prices(models)
    print(f"Fetched {len(prices)} models")

    snapshot = load_snapshot()
    if snapshot:
        changes = find_price_changes(prices, snapshot)
        if changes:
            print(f"Found {len(changes)} price changes:")
            for c in changes:
                print(f"  {c['model']} ({c['type']}): {c['old']} -> {c['new']}")
        else:
            print("No price changes detected")
    else:
        print("No previous snapshot found")

    save_snapshot(prices)
    print("Snapshot saved")


if __name__ == "__main__":
    main()
