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
            "price_per_1k_input": float(model.get("pricing", {}).get("prompt", 0) or 0),
            "price_per_1k_output": float(model.get("pricing", {}).get("completion", 0) or 0),
            "context_length": model.get("context_length") or model.get("max_tokens"),
            "updated_at": model.get("updated_at", ""),
        }
        for model in models
    ]


def send_discord_alert(message):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("WARNING: DISCORD_WEBHOOK not set, skipping Discord alert")
        return

    print("Discord webhook configured, sending message...")
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


def find_changes(current, previous):
    alerts = []
    prev_by_id = {m["id"]: m for m in previous}
    current_ids = set(m["id"] for m in current)
    prev_ids = set(prev_by_id.keys())

    # New models
    new_models = current_ids - prev_ids
    for model_id in new_models:
        model = next(m for m in current if m["id"] == model_id)
        alerts.append(f"🆕 {model['provider'].capitalize()}: {model['name']} added")

    # Price changes
    for model in current:
        prev = prev_by_id.get(model["id"])
        if not prev:
            continue

        was_free = prev["price_per_1k_input"] == 0 and prev["price_per_1k_output"] == 0
        is_free = model["price_per_1k_input"] == 0 and model["price_per_1k_output"] == 0

        if not was_free and is_free:
            alerts.append(f"🎉 {model['provider'].capitalize()}: {model['name']} went free!")

        old_total = float(prev["price_per_1k_input"]) + float(prev["price_per_1k_output"])
        new_total = float(model["price_per_1k_input"]) + float(model["price_per_1k_output"])

        if old_total > new_total and abs(old_total - new_total) > 1e-6:
            alerts.append(
                f"💸 {model['provider'].capitalize()}: {model['name']} price dropped (${old_total:.6f} → ${new_total:.6f})"
            )

    return alerts


def group_free_models(models):
    free_models = [
        m for m in models
        if m["price_per_1k_input"] == 0 and m["price_per_1k_output"] == 0
    ]
    grouped = {}
    for m in free_models:
        provider = m["provider"].capitalize()
        grouped.setdefault(provider, []).append(m["name"])

    return grouped


def send_grouped_free_models(models):
    grouped = group_free_models(models)
    if not grouped:
        print("No free models found")
        return

    sections = []
    for provider in sorted(grouped):
        names = sorted(grouped[provider])
        lines = "\n".join(f"• {name}" for name in names)
        sections.append(f"**{provider}**\n{lines}")

    message = "💰 **OpenRouter Free Models**\n\n" + "\n\n".join(sections)
    send_discord_alert(message)


def main():
    print(f"[{datetime.now().isoformat()}] Fetching models...")
    models = fetch_models()
    prices = extract_prices(models)
    print(f"Fetched {len(prices)} models")

    if os.getenv("TEST_DISCORD"):
        send_discord_alert("🧪 **Test Message:** Discord webhook is working!")
        print("Test message sent")
        return

    snapshot = load_snapshot()
    if snapshot:
        alerts = find_changes(prices, snapshot)
        if alerts:
            print(f"Found {len(alerts)} changes:")
            for a in alerts:
                print(f"  {a}")
            send_discord_alert("🔔 **OpenRouter Updates:**\n" + "\n".join(alerts))
        else:
            print("No changes detected")
    else:
        print("No previous snapshot found")

    # Send free models grouped by provider
    send_grouped_free_models(prices)

    save_snapshot(prices)
    print("Snapshot saved")


if __name__ == "__main__":
    main()
