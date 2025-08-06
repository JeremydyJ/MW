import requests
import time
import json
import uuid

# === CONFIGURATION ===
BET_URL = "https://u13.ns86.kingmakergames.co/table/api/single_plays/batch_create"
LOBBY_ID = "65b9e8fdabbd4f00d66666cd"
TOKEN = "aaa3584aaf76f3d2733339074cdee2f3"  # 使用你 Expert 测试时的 token
CLIENT_ID = "c927a7f2a4db52d24940ff3ca83dd862"

HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json;charset=UTF-8",
    "game-identifier": "plinko",
    "origin": "https://cdn.kingmidasdev.net",
    "referer": "https://cdn.kingmidasdev.net/",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "x-authentication-token": TOKEN,
    "x-client-id": CLIENT_ID,
}

ROOMS = {
    "casual": {
        "table": "plko-blue-mid",
        "chips": [10, 20, 30, 50, 100, 200]
    },
    "expert": {
        "table": "plko-yellow-mid",
        "chips": [100, 200, 300, 500, 1000, 2000]
    }
}

def place_bet(table_name, chip_amount):
    payload = {
        "bet_batch_table": {
            table_name: [chip_amount]
        },
        "single_play": {
            "lobbyId": LOBBY_ID
        },
        "extra_params": {
            "uuid": str(uuid.uuid4())
        }
    }

    print(f"[INFO] Placing bet: {table_name} with chip {chip_amount}")
    try:
        response = requests.post(BET_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"[SUCCESS] Result: {result}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Bet failed: {e}")
        return None

if __name__ == "__main__":
    all_results = []
    for room_name, room_data in ROOMS.items():
        table = room_data["table"]
        chips = room_data["chips"]
        for chip in chips:
            result = place_bet(table, chip)
            all_results.append({
                "room": room_name,
                "table": table,
                "chip": chip,
                "result": result
            })
            time.sleep(1.5)

    with open("expert_and_casual_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    print("[INFO] All bets completed and results saved to 'expert_and_casual_results.json'")
