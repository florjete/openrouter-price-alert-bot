import json
import os
import requests
from datetime import datetime

API_URL = "https://openrouter.ai/api/v1/models"
SNAPSHOT_FILE = "models_snapshot.json"

# Set TEST_DISCORD=1 to print messages instead of sending to Discord
TEST_MODE = os.getenv("TEST_DISCORD") == "1"


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


def format_price(p):
    return f"${p:.6f}".rstrip("0").rstrip(".")


def send_discord_alert(message):
    if TEST_MODE:
        print("=== Discord Alert (TEST MODE) ===")
        print(message)
        print("=== End of Alert ===\n")
        return

    webhook_url = os.getenv("DISCORD_WEBHOOK")
    if not webhook_url:
        print("WARNING: DISCORD_WEBHOOK not set, skipping Discord alert")
        return

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
            return json.loads(content) if content else []
    except FileNotFoundError:
        return []


def save_snapshot(data):
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_and_group_alerts(current, previous):
    grouped = {}
    prev_by_id = {m["id"]: m for m in previous} if previous else {}

    for model in current:
        provider = model["provider"].capitalize()
        grouped.setdefault(provider, [])

        # Model link
        url = f"https://openrouter.ai/chat?models={model['id']}"
        link_name = f"[{model['name']}]({url})"

        prev = prev_by_id.get(model["id"])

        # First run or new model
        if not prev:
            grouped[provider].append(f"🆕 {link_name} added")
            continue

        # Free check
        was_free = prev["price_per_1k_input"] == 0 and prev["price_per_1k_output"] == 0
        is_free = model["price_per_1k_input"] == 0 and model["price_per_1k_output"] == 0
        if not was_free and is_free:
            grouped[provider].append(f"🎉 {link_name} went free!")

        # Price drop
        old_total = float(prev["price_per_1k_input"]) + float(prev["price_per_1k_output"])
        new_total = float(model["price_per_1k_input"]) + float(model["price_per_1k_output"])
        if old_total > new_total and abs(old_total - new_total) > 1e-6:
            grouped[provider].append(
                f"💸 {link_name} price dropped ({format_price(old_total)} → {format_price(new_total)})"
            )

    return grouped


def send_grouped_alerts(grouped_alerts):
    # Only send if at least one provider has alerts
    if not any(grouped_alerts.values()):
        return

    sections = []
    for provider in sorted(grouped_alerts):
        if not grouped_alerts[provider]:
            continue
        lines = "\n".join(grouped_alerts[provider])
        sections.append(f"**{provider}**\n{lines}")

    message = "🔔 **OpenRouter Updates**\n\n" + "\n\n".join(sections)
    send_discord_alert(message)


def main():
    print(f"[{datetime.now().isoformat()}] Fetching models...")
    models = fetch_models()
    prices = extract_prices(models)
    print(f"Fetched {len(prices)} models")

    snapshot = load_snapshot()
    grouped_alerts = find_and_group_alerts(prices, snapshot)

    # Send alerts only if there are updates
    send_grouped_alerts(grouped_alerts)

    save_snapshot(prices)
    print("Snapshot saved")


if __name__ == "__main__":
    main()
