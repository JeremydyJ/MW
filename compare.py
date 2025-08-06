import gspread
from google.oauth2.service_account import Credentials

# ---------- 授权 ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)

# ---------- 加载文档 ----------
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_sheet_url = "https://docs.google.com/spreadsheets/d/1bRCqItJyoxecxHDXC-pwrAP-4ZXfHovdceA6RqhGg2A/edit"
sheet_round = gc.open_by_url(sheet_url).worksheet("testing")
sheet_singleplay = gc.open_by_url(sheet_url).worksheet("test2")
ref_doc = gc.open_by_url(ref_sheet_url)

# ---------- 辅助函数 ----------
def batch_append_rows(ws, headers, rows):
    if not rows:
        return
    try:
        ws.clear()
    except:
        pass
    ws.append_row(headers)
    for i in range(0, len(rows), 200):
        chunk = rows[i:i+200]
        ws.append_rows(chunk)

# ---------- 映射表 ----------
ref_ws_single = ref_doc.worksheet("M13 Single Player")
ref_data_single = ref_ws_single.get_all_values()
ref_mapping_single = {}
for row in ref_data_single[1:]:
    game_id = row[0].strip().lower()
    hkd = row[5].strip() if len(row) > 5 else ""
    if '-' in hkd:
        try:
            min_val, max_val = map(float, hkd.split("-"))
            ref_mapping_single[game_id] = {"min": min_val, "max": max_val}
        except:
            continue

ref_ws_table = ref_doc.worksheet("M13 Table Games")
ref_data_table = ref_ws_table.get_all_values()
ref_mapping_table = {}
for row in ref_data_table[1:]:
    key = row[0].strip().lower()
    hkd = row[5].strip() if len(row) > 5 else ""
    if '-' in hkd:
        try:
            min_val, max_val = map(float, hkd.split("-"))
            ref_mapping_table[key] = {"min": min_val, "max": max_val}
        except:
            continue

room_map = {
    ("video poker", "Friendly"): "video-poker-1",
    ("video poker", "Casual"): "video-poker-2",
    ("video poker", "Expert"): "video-poker-3",
    ("video poker", "High Roller"): "video-poker-4",
    ("heist", "Lobby 1"): "single-player-games-1",
    ("bola-tangkas", "Friendly"): "bola-tangkas-1",
    ("bola-tangkas", "Casual"): "bola-tangkas-2",
    ("bola-tangkas", "Expert"): "bola-tangkas-3",
    ("bola-tangkas", "High Roller"): "bola-tangkas-4",
    ("plinko", "Lobby 1"): "single-player-games-1",
    ("card-hi-lo", "Friendly"): "card-hi-lo-1",
    ("card-hi-lo", "Casual"): "card-hi-lo-2",
    ("card-hi-lo", "Expert"): "card-hi-lo-3",
    ("card-hi-lo", "High Roller"): "card-hi-lo-4",
    ("egyptian-mines", "Lobby 1"): "single-player-games-1",
    ("mine-sweeper", "Lobby 1"): "single-player-games-1"
}

room_suffixes = {
    "Casual": "table-games-casual",
    "Novice": "table-games-novice",
    "Expert": "table-games-expert",
    "High Roller": "table-games-high-roller",
    "Lobby 1": "table-games-lobby-1"
}

# ✅ 补充 cash-rocket 特例
special_room_map = {
    ("cash-rocket", "Casual"): "cash-rocket-1",
    ("cash-rocket", "Novice"): "cash-rocket-2",
    ("cash-rocket", "Expert"): "cash-rocket-3",
    ("cash-rocket", "High Roller"): "cash-rocket-4"
}

room_map.update(special_room_map)

special_three_lobby = ["colour game mega bonus", "andar-bahar-2", "teen patti blitz", "dice duet", "ladder game", "jogo-de-bozo"]

# ---------- 比对函数 ----------
def compare_and_write_results(source_ws, result_sheet_name):
    pull_data = source_ws.get_all_records()
    rows = []
    for row in pull_data:
        game = row['Game'].strip().lower()
        room = row['Room Name'].strip()
        try:
            minBet = float(row['minBet'])
            maxBet = float(row['maxBet'])
        except:
            continue
        ref_key = room_map.get((game, room))
        if ref_key and ref_key in ref_mapping_single:
            expected = ref_mapping_single[ref_key]
            status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
            rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
        else:
            rows.append([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING"])
    batch_append_rows(source_ws.spreadsheet.worksheet(result_sheet_name), 
                      ["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status"], 
                      rows)

def compare_table_game_results(source_ws, result_sheet_name):
    pull_data = source_ws.get_all_records()
    rows = []
    for row in pull_data:
        game = row['Game'].strip().lower()
        room = row['Room Name'].strip()
        try:
            minBet = float(row['minBet'])
            maxBet = float(row['maxBet'])
        except:
            continue
        special_key = room_map.get((game, room))
        if special_key and special_key in ref_mapping_table:
            expected = ref_mapping_table[special_key]
            status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
            rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
        elif game in special_three_lobby:
            alt_key = f"three-lobby-{room.strip().lower().replace(' ', '-')}"
            if alt_key in ref_mapping_table:
                expected = ref_mapping_table[alt_key]
                status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
                rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
            else:
                rows.append([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING"])
        else:
            suffix_key = room_suffixes.get(room)
            if suffix_key and suffix_key in ref_mapping_table:
                expected = ref_mapping_table[suffix_key]
                status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
                rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
            else:
                rows.append([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING"])
    batch_append_rows(source_ws.spreadsheet.worksheet(result_sheet_name), 
                      ["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status"], 
                      rows)

# ---------- 主程序 ----------
if __name__ == "__main__":
    print("[📊] 开始比对 Singleplay...")
    compare_and_write_results(sheet_singleplay, "Result singleplay(HKD)")

    print("[📊] 开始比对 Round/Table...")
    compare_table_game_results(sheet_round, "Result Round Based Game/ Table Games (HKD)")

    print("[✅] 比对完成")
