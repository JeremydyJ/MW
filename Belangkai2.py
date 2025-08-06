import requests

# ✅ Your actual API endpoint
url = "https://m13.ns86.kingdomhall729.com/table/api/lobbies/5db8395dd3747f03f7c340e6/room_members"

# ✅ Headers copied from your browser's Network tab
headers = {
    "Accept": "*/*",
    "Game-Identifier": "belangkai-2",
    "Origin": "https://cdn.kingdomhall729.com",
    "Referer": "https://cdn.kingdomhall729.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.1 Safari/605.1.15",
    "X-Authentication-Token": "e5861be5c09b4825ab35812358322c30",
    "X-Client-Id": "c927a7f2a4db52d24940ff3ca83dd862"
}

# ✅ Send the request
response = requests.get(url, headers=headers)

# ✅ Parse the result
if response.status_code == 200:
    data = response.json()
    print("✅ API call success")

    # 🔍 Print data to inspect structure
    import json
    print(json.dumps(data, indent=2))  # Temporarily print nicely

    # ✅ Try extracting min_bet / max_bet
    for room in data.get("data", []):
        room_id = room.get("room_id")
        min_bet = room.get("min_bet")
        max_bet = room.get("max_bet")

        print(f"Room: {room_id} | Min Bet: {min_bet} | Max Bet: {max_bet}")

        # ✅ Optional check/assertion
        expected_min = 10
        expected_max = 500
        if min_bet != expected_min:
            print(f"❌ Min bet mismatch! Expected: {expected_min}, Got: {min_bet}")
        if max_bet != expected_max:
            print(f"❌ Max bet mismatch! Expected: {expected_max}, Got: {max_bet}")
else:
    print(f"❌ Failed to fetch data. Status code: {response.status_code}")
