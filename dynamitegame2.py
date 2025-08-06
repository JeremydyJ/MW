import requests
import time
import json
from uuid import uuid4

# === CONFIGURATION ===
BET_URL = "https://u13.ns86.kingmakergames.co/table/api/single_plays/batch_create"
LOBBY_ID = "65b9e8fdabbd4f00d66666cd"
CLIENT_ID = "c927a7f2a4db52d24940ff3ca83dd862"

# 替换成你的 TOKEN（每种币种应有不同 TOKEN，如需）
TOKEN_MAP = {
    "THB": "c07e249bf299edc3a0907fb5b554a4fa",
    "GSK": "4705176a386a2ce6a2e830522029d8ee"
}

HEADERS_TEMPLATE = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json;charset=UTF-8",
    "game-identifier": "plinko",
    "origin": "https://cdn.kingmidasdev.net",
    "referer": "https://cdn.kingmidasdev.net/",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "x-client-id": CLIENT_ID,
}

# === CHIP VALUES ===
CHIP_VALUES = {
    "THB": [10, 20, 30, 50, 100, 200, 300, 500, 1000, 2000, 3000],
    "GSK": [1, 2, 3, 5, 10, 20, 30, 50, 100, 200]
}

# 固定 table name，服务端会自动根据金额+币种分配房间
TABLE_NAME = "plko-blue-mid"

def place_bet(currency: str, chip: int):
    headers = HEADERS_TEMPLATE.copy()
    headers["x-authentication-token"] = TOKEN_MAP[currency]

    payload = {
        "bet_batch_table": {
            TABLE_NAME: [chip]
        },
        "single_play": {
            "lobbyId": LOBBY_ID
        },
        "extra_params": {
            "uuid": str(uuid4())[:10]
        }
    }

    print(f"[INFO] Placing bet: currency={currency}, chip={chip}")
    try:
        response = requests.post(BET_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"[SUCCESS] -> {result}")
        return {
            "currency": currency,
            "chip": chip,
            "table": TABLE_NAME,
            "response": result,
            "success": True
        }
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Bet failed: {e}")
        return {
            "currency": currency,
            "chip": chip,
            "table": TABLE_NAME,
            "error": str(e),
            "success": False
        }

if __name__ == "__main__":
    all_results = []
    for currency in CHIP_VALUES:
        for chip in CHIP_VALUES[currency]:
            result = place_bet(currency, chip)
            all_results.append(result)
            time.sleep(1.5)  # 控制下注频率

    with open("gsk_thb_bet_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

    print("[INFO] ✅ All bets completed and saved to 'gsk_thb_bet_results.json'")
