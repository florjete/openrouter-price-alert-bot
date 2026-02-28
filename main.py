import json
import os
import requests
from datetime import datetime

API_URL = "https://openrouter.ai/api/v1/models"
SNAPSHOT_FILE = "models_snapshot.json"


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


def send_discord_alert(message):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("WARNING: DISCORD_WEBHOOK not set, skipping Discord alert")
        return

    print(f"Discord webhook configured, sending message...")
    try:
        response = requests.post(webhook_url, json={"content": message}, timeout=10)
        print(f"Discord response status: {response.status_code}")
        if response.status_code not in (200, 204):
            print(f"WARNING: Discord webhook returned {response.status_code}")
            print(f"Response: {response.text}")
    except requests.RequestException as e:
        print(f"WARNING: Failed to send Discord alert: {e}")


def load_snapshot():
    try:
        with open(SNAPSHOT_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
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


def get_free_models(models):
    free = [m for m in models if m["price_per_1k_input"] == "0" or m["price_per_1k_output"] == "0"]
    return [
        {
            "id": m["id"],
            "name": m["name"],
            "provider": m["provider"],
            "price_input": round(float(m["price_per_1k_input"]), 4),
            "price_output": round(float(m["price_per_1k_output"]), 4),
        }
        for m in free
    ][:10]


def send_free_models_to_discord(free_models):
    if not free_models:
        print("No free models found")
        return
    message = "💰 **Free Models:**\n" + "\n".join(
        f"- {m['name']} (in:${m['price_input']}/out:${m['price_output']})"
        for m in free_models
    )
    print(f"Sending {len(free_models)} cheapest models to Discord")
    send_discord_alert(message)


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
            send_discord_alert(f"🚨 {len(changes)} price change(s) detected")
        else:
            print("No price changes detected")
    else:
        print("No previous snapshot found")

    save_snapshot(prices)
    print("Snapshot saved")

    free_models = get_free_models(prices)
    print(f"Found {len(free_models)} free models")
    send_free_models_to_discord(free_models)


if __name__ == "__main__":
    main()
