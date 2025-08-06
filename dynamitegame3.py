import requests
import time
import uuid

# 房间与 THB 筹码设置（每个房间 6 个筹码）
rooms = {
    "Casual": {
        "lobby_id": "6834a5ef6d0a19000cec41ec",
        "chips": [10, 20, 30, 50, 100, 200]
    },
    "Novice": {
        "lobby_id": "65b9e8fdabbd4f00d66666ce",
        "chips": [20, 30, 50, 100, 200, 500]
    },
    "Expert": {
        "lobby_id": "65b9e8fdabbd4f00d66666cf",
        "chips": [100, 200, 300, 500, 1000, 2000]
    },
    "High Roller": {
        "lobby_id": "6834a48d6d0a19000cec41e6",
        "chips": [200, 300, 500, 1000, 2000, 3000]
    }
}

# 请求头（请确保 token 与 client ID 正确）
headers = {
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://cdn.kingmidasdev.net",
    "referer": "https://cdn.kingmidasdev.net/",
    "x-authentication-token": "d3978e2ea582f5a51b1b0e082eef4c06",
    "x-client-id": "c927a7f2a4db52d24940ff3ca83dd862",
    "game-identifier": "fan-tan-3"
}

endpoint = "https://u13.ns86.kingmakergames.co/table/api/bets/batch_create"

# 多个下注选项
bet_options = [
    "ft-3-4-kwok",
    "ft-1-2-kwok"
]

# 测试函数
def test_room(room_name, room_data):
    print(f"[INFO] Testing room: {room_name}")
    for chip in room_data["chips"]:
        for bet_option in bet_options:
            payload = {
                "bets": [
                    {
                        "betOption": bet_option,
                        "stakes": [chip]
                    }
                ]
            }
            try:
                response = requests.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    print(f"  [PASS] Bet {bet_option} with chip {chip} success.")
                else:
                    try:
                        error = response.json()
                    except Exception:
                        error = response.text
                    print(f"  [FAIL] Bet {bet_option} with chip {chip} failed. Status: {response.status_code}, Error: {error}")
            except requests.exceptions.RequestException as e:
                print(f"  [ERROR] Request failed: {e}")
            time.sleep(1)

# 执行所有房间测试
for room_name, room_data in rooms.items():
    test_room(room_name, room_data)
    print("-------------------------------------------")
