import requests

# === Step 1: 登录后台（验证用户名密码） ===
login_url = "https://uatmwapi.kmgamesdev.net/Login/User"
login_payload = {
    "name": "qa",
    "password": "$2b$10$f99DAu.ViVP9BfJQBFQzl.Bw0gwY6tjacpe74vpGS9n4tQQulWQbu"
}
login_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://uatmw.kmgamesdev.net",
    "Referer": "https://uatmw.kmgamesdev.net/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

login_response = requests.post(login_url, json=login_payload, headers=login_headers)
if login_response.status_code != 200:
    print("[❌] 登入后台失败")
    exit()
print("[✅] 成功登入游戏后台")

# === Step 2: 设置 player login name 并获取 token ===
nickname = "Jeremyhkd"
player_login_url = f"https://uat.kmgamesdev.net/integration/login?nickname={nickname}&client=awc"
player_login_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://uatmw.kmgamesdev.net",
    "Referer": "https://uatmw.kmgamesdev.net/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

player_login_response = requests.post(player_login_url, headers=player_login_headers)
if player_login_response.status_code != 200:
    print("[❌] 设定 Player Login Name 失败")
    print(player_login_response.text)
    exit()
print("[✅] 成功设定 Player Login Name")

# ✅ 从响应中提取 token
player_data = player_login_response.json()
token = player_data.get("token")
if not token:
    print("[❌] 未能从响应中获取 token")
    exit()

print("[🔑] 获取到 token：", token[:20] + "...")  # 部分展示避免过长

# === Step 3: 检查多个房间 minBet ===
room_ids = [
    "5e145e43e8af890e844b4dee",
    "5e145e45e8af890e844b4df5"
]
game_identifier = "baccarat"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"  # 固定使用（或也可以从别处动态获取）

room_url = "https://m13.ns86.kingdomhall729.com/table/api/room_members.json"
room_headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "*/*",
    "Origin": "https://cdn.kingdomhall729.com",
    "Referer": "https://cdn.kingdomhall729.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "x-authentication-token": token,
    "x-client-id": client_id,
    "game-identifier": game_identifier
}

def check_min_bet(room_id: str):
    response = requests.post(room_url, headers=room_headers, json={"room_id": room_id})
    if response.status_code != 200:
        print(f"[❌] Room {room_id} 请求失败，状态码 {response.status_code}")
        print(response.text)
        return

    try:
        data = response.json()
        min_bet = data.get("roomMember", {}).get("room", {}).get("minBet")
        if min_bet is None:
            print(f"[⚠️] Room {room_id} 响应中未找到 minBet")
        elif min_bet == 1.0:
            print(f"[✅] Room {room_id} 的 minBet 为 1.0")
        else:
            print(f"[⚠️] Room {room_id} 的 minBet = {min_bet}，应为 1.0")
    except Exception as e:
        print(f"[❌] 解析 Room {room_id} JSON 出错：{e}")
        print(response.text)

print("\n🔍 正在检查房间 minBet...\n")
for rid in room_ids:
    check_min_bet(rid)
