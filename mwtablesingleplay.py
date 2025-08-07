from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests
import json
import gspread
from google.oauth2.service_account import Credentials

# ---------- Configuration ----------
username = "qa"
password = "qa123456"
login_url = "https://uatmw.kmgamesdev.net/"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"
lobbies_url = "https://m13.ns86.kingdomhall729.com/table/api/lobbies"
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_sheet_url = "https://docs.google.com/spreadsheets/d/1bRCqItJyoxecxHDXC-pwrAP-4ZXfHovdceA6RqhGg2A/edit"

# Initialize Google Sheets
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_url(sheet_url)
nickname_ws = spreadsheet.worksheet("nickname")

# ---------- Game Mappings ----------
round_display_to_identifier = {
    "baccarat": "baccarat",
    "cash-rocket": "cash-rocket",
    "belangkai-2": "belangkai-2",
    "colour game mega bonus": "colour-game-2",
    "color-game": "color-game",
    "andar-bahar": "andar-bahar",
    "andar-bahar-2": "andar-bahar-2",
    "teen patti blitz": "teen-patti-2",
    "dice duet": "dice-duet",
    "thirty-two-cards": "thirty-two-cards",
    "dragon-tiger-2": "dragon-tiger-2",
    "sicbo": "sicbo",
    "jhandi-munda": "jhandi-munda",
    "thai-fish-prawn-crab": "thai-fish-prawn-crab",
    "fruit-roulette": "fruit-roulette",
    "fan-tan-3": "fan-tan-3",
    "viet-fish-prawn-crab": "viet-fish-prawn-crab",
    "xoc-dia-2": "xoc-dia-2",
    "ladder game": "ladder-game",
    "monkey-king-roulette": "monkey-king-roulette",
    "seven-up-down": "seven-up-down",
    "bola-golek": "bola-golek",
    "bonus-dice": "bonus-dice",
    "coin-toss": "coin-toss",
    "jogo-de-bozo": "jogo-de-bozo",
    "thai-hi-lo": "thai-hi-lo-2"
}
round_game_list = list(round_display_to_identifier.keys())

singleplay_display_to_identifier = {
    "heist": "heist",
    "Mine-sweeper": "Mine-sweeper",
    "Plinko": "Plinko",
    "Card-hi-lo": "Card-hi-lo",
    "Bola-tangkas": "Bola-tangkas",
    "video poker": "video-poker",
    "Egyptian-mines": "Egyptian-mines"
}
singleplay_game_list = list(singleplay_display_to_identifier.keys())

# ---------- Utility Functions ----------
def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")

def batch_append_rows(ws, headers, data):
    if data:
        col_end = chr(ord('A') + len(headers) - 1)
        ws.batch_clear([f"A2:{col_end}1000"])
    ws.update('A1', [headers])
    if not data:
        return
    max_batch_size = 500
    for i in range(0, len(data), max_batch_size):
        chunk = data[i:i + max_batch_size]
        start_row = i + 2
        end_row = start_row + len(chunk) - 1
        cell_range = f"A{start_row}:{chr(ord('A') + len(headers) - 1)}{end_row}"
        ws.batch_update([{'range': cell_range, 'values': chunk}])

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    return webdriver.Chrome(options=chrome_options)

def login_and_set_nickname(driver, wait, nickname):
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter user name']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter password']"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print("[🔐] Login successful, setting nickname...")
    wait.until(EC.url_contains("/LoginTestPlayer"))
    nickname_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter login name']")))
    nickname_input.clear()
    nickname_input.send_keys(nickname)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()

def wait_for_token_in_storage(driver, timeout=20):
    start_time = time.time()
    for i in range(timeout):
        local_storage = driver.execute_script("return JSON.stringify(window.localStorage);")
        session_storage = driver.execute_script("return JSON.stringify(window.sessionStorage);")
        all_storage = {**json.loads(local_storage), **json.loads(session_storage)}
        for k, v in all_storage.items():
            if "token" in k.lower() or "authentication" in k.lower():
                duration = round(time.time() - start_time, 2)
                print(f"[🔑] Got token: key = {v}, took: {duration} seconds")
                return v
        time.sleep(1)
    print("[❌] Timeout getting token")
    return None

# ---------- Reference Data Loading ----------
def build_ref_mappings(ref_doc, currency_code):
    # Single Player reference mapping
    ref_ws_single = ref_doc.worksheet("M13 Single Player")
    ref_data_single = ref_ws_single.get_all_values()
    ref_mapping_single = {}
    
    # Find currency column index
    if len(ref_data_single) > 0:
        header = ref_data_single[0]
        currency_col = None
        for idx, col in enumerate(header):
            if col.strip().upper() == currency_code:
                currency_col = idx
                break
    
    if currency_col is None:
        raise ValueError(f"Currency column '{currency_code}' not found in reference sheet")
    
    for row in ref_data_single[1:]:
        game_id = row[0].strip().lower()
        if len(row) > currency_col:
            cell = row[currency_col].strip()
            if '-' in cell:
                try:
                    min_val, max_val = map(float, cell.split('-'))
                    ref_mapping_single[game_id] = {"min": min_val, "max": max_val}
                except:
                    continue

    # Table Games reference mapping
    ref_ws_table = ref_doc.worksheet("M13 Table Games")
    ref_data_table = ref_ws_table.get_all_values()
    ref_mapping_table = {}
    
    # Find currency column index (same header structure assumed)
    if len(ref_data_table) > 0:
        header = ref_data_table[0]
        currency_col = None
        for idx, col in enumerate(header):
            if col.strip().upper() == currency_code:
                currency_col = idx
                break
    
    if currency_col is None:
        raise ValueError(f"Currency column '{currency_code}' not found in reference sheet")
    
    for row in ref_data_table[1:]:
        key = row[0].strip().lower()
        if len(row) > currency_col:
            cell = row[currency_col].strip()
            if '-' in cell:
                try:
                    min_val, max_val = map(float, cell.split('-'))
                    ref_mapping_table[key] = {"min": min_val, "max": max_val}
                except:
                    continue

    return ref_mapping_single, ref_mapping_table

def build_room_mappings():
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
        ("mine-sweeper", "Lobby 1"): "single-player-games-1",
        ("cash-rocket", "Casual"): "cash-rocket-1",
        ("cash-rocket", "Novice"): "cash-rocket-2",
        ("cash-rocket", "Expert"): "cash-rocket-3",
        ("cash-rocket", "High Roller"): "cash-rocket-4"
    }

    room_suffixes = {
        "Casual": "table-games-casual",
        "Novice": "table-games-novice",
        "Expert": "table-games-expert",
        "High Roller": "table-games-high-roller",
        "Lobby 1": "table-games-lobby-1"
    }

    special_three_lobby = [
        "colour game mega bonus", 
        "andar-bahar-2", 
        "teen patti blitz", 
        "dice duet", 
        "ladder game", 
        "jogo-de-bozo"
    ]

    return room_map, room_suffixes, special_three_lobby

# ---------- Game Execution ----------
def run_game_and_get_info(driver, wait, nickname, game_name, game_identifier, buffer, include_chips=False):
    print(f"\n============== Processing {nickname} game: {game_name} ==============")
    try:
        # Search for game
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='search by game']")))
        driver.execute_script("arguments[0].value = '';", search_box)
        time.sleep(1)
        search_js = f'''
            const input = document.querySelector("input[placeholder='search by game']");
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(input, "{game_name}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        '''
        driver.execute_script(search_js)
        print(f"[🔍] Searching game: {game_name}")
        time.sleep(1.5)
        
        # Launch game
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Launch')]"))).click()
        print(f"[🚀] Launching game: {game_name}")
        time.sleep(5)
        driver.switch_to.window(driver.window_handles[-1])
        print("[🪟] Switched to game tab")
        time.sleep(12)

        # Get token
        token = wait_for_token_in_storage(driver)
        if not token:
            raise Exception("❌ Failed to get token")
            
        # Make API request
        headers = {
            "x-authentication-token": token,
            "x-client-id": client_id,
            "content-type": "application/json",
            "origin": "https://cdn.kingdomhall729.com",
            "referer": "https://cdn.kingdomhall729.com/",
            "game-identifier": game_identifier
        }

        print(f"[🌐] Requesting lobbies API: {lobbies_url}")
        response = requests.get(lobbies_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"[❌] API request failed: {response.status_code}")

        # Process response
        data = response.json()
        seen = set()
        for lobby in data.get("lobbies", []):
            name = lobby.get("name", "Unknown room")
            min_bet = lobby.get("minBet", "?")
            max_bet = lobby.get("maxBetTag", "?")
            chips = lobby.get("availableChipOptions", []) if include_chips else None
            chips_str = ", ".join(map(str, chips)) if chips else ""
            key = (name, min_bet, max_bet, chips_str)
            if key not in seen:
                seen.add(key)
                print(f" - {name} | minBet: {min_bet} | maxBet: {max_bet}" + (f" | Chips: {chips_str}" if include_chips else ""))
                row = [game_name, name, min_bet, max_bet]
                if include_chips:
                    row.append(chips_str)
                buffer.append(row)
        
        # Clean up
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return True
    except Exception as e:
        print(f"[❌] Failed: {game_name}, error: {e}")
        return False
    finally:
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except:
            pass

# ---------- Comparison Logic ----------
def get_comparison_status(actual_min, actual_max, expected):
    if actual_min == expected['min'] and actual_max == expected['max']:
        return "✅ PASS", ""
    elif actual_min == expected['min']:
        return "✅ PASS", f"⚠️ MaxBet mismatch: expected {expected['max']}"
    else:
        return "❌ FAILED", f"Expected min: {expected['min']}, max: {expected['max']}"

def compare_results(source_ws, result_sheet_name, ref_mapping, room_map, room_suffixes, special_three_lobby):
    result_ws = get_or_create_worksheet(source_ws.spreadsheet, result_sheet_name)
    pull_data = source_ws.get_all_records()
    rows = []

    for row in pull_data:
        try:
            game = row['Game'].strip().lower()
            room = row['Room Name'].strip()
            minBet = float(row['minBet'])
            maxBet = float(row['maxBet'])
        except:
            continue

        # First check special room mapping
        ref_key = room_map.get((game, room))
        if ref_key and ref_key in ref_mapping:
            expected = ref_mapping[ref_key]
            status, remark = get_comparison_status(minBet, maxBet, expected)
            rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status, remark])
            continue

        # Check for special three lobby games
        if game in special_three_lobby:
            alt_key = f"three-lobby-{room.strip().lower().replace(' ', '-')}"
            if alt_key in ref_mapping:
                expected = ref_mapping[alt_key]
                status, remark = get_comparison_status(minBet, maxBet, expected)
                rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status, remark])
                continue

        # Check room suffixes
        suffix_key = room_suffixes.get(room)
        if suffix_key and suffix_key in ref_mapping:
            expected = ref_mapping[suffix_key]
            status, remark = get_comparison_status(minBet, maxBet, expected)
            rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status, remark])
            continue

        # No mapping found
        rows.append([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING", "-"])
    
    batch_append_rows(result_ws,
                     ["Game", "Room Name", "Actual minBet", "Actual maxBet", 
                      "Expected minBet", "Expected maxBet", "Status", "Remark"],
                     rows)

# ---------- Main Program ----------
if __name__ == "__main__":
    for row in nickname_ws.get_all_records():
        nickname = row.get("nickname", "").strip()
        currency = row.get("currency", "").strip().upper()
        if not nickname or not currency:
            continue
        print(f"\n======================= 👤 Processing: {nickname} ({currency}) =======================")
        
        try:
            # Load reference data
            ref_doc = gc.open_by_url(ref_sheet_url)
            ref_mapping_single, ref_mapping_table = build_ref_mappings(ref_doc, currency)
            room_map, room_suffixes, special_three_lobby = build_room_mappings()
            
            # Create worksheets
            round_sheet = get_or_create_worksheet(spreadsheet, f"Round Based ({currency})")
            singleplay_sheet = get_or_create_worksheet(spreadsheet, f"Singleplay ({currency})")
            
            buffer_round = []
            buffer_singleplay = []
            retry_round = []
            retry_singleplay = []

            # Initialize driver
            driver = create_driver()
            wait = WebDriverWait(driver, 20)
            login_and_set_nickname(driver, wait, nickname)

            # Process Round Based Games
            for game in round_game_list:
                identifier = round_display_to_identifier.get(game.lower(), game.lower())
                success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_round)
                if not success:
                    retry_round.append(game)

            # Process Singleplay Games
            for game in singleplay_game_list:
                identifier = singleplay_display_to_identifier.get(game.lower(), game.lower())
                success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_singleplay, include_chips=True)
                if not success:
                    retry_singleplay.append(game)

            # Save initial results
            batch_append_rows(round_sheet, 
                            ["Game", "Room Name", "minBet", "maxBet"], 
                            buffer_round)
            batch_append_rows(singleplay_sheet, 
                            ["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"], 
                            buffer_singleplay)
            
            # Compare results
            compare_results(round_sheet, f"Result Round Based ({currency})", 
                          ref_mapping_table, room_map, room_suffixes, special_three_lobby)
            compare_results(singleplay_sheet, f"Result Singleplay ({currency})", 
                          ref_mapping_single, room_map, room_suffixes, special_three_lobby)
            
            print(f"[✅] {nickname} ({currency}) completed ✅")
            
        except Exception as e:
            print(f"[❌] Error processing {nickname} ({currency}): {e}")
        finally:
            try:
                driver.quit()
            except:
                pass

        # Retry failed games
        if retry_round or retry_singleplay:
            print(f"[🔁] Retrying games - Round: {retry_round}, Singleplay: {retry_singleplay}")
            buffer_retry_round = []
            buffer_retry_singleplay = []
            
            try:
                driver = create_driver()
                wait = WebDriverWait(driver, 20)
                login_and_set_nickname(driver, wait, nickname)
                
                for game in retry_round:
                    identifier = round_display_to_identifier.get(game.lower(), game.lower())
                    success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_retry_round)
                    if not success:
                        print(f"[❌] Final failure: {game}")
                
                for game in retry_singleplay:
                    identifier = singleplay_display_to_identifier.get(game.lower(), game.lower())
                    success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_retry_singleplay, include_chips=True)
                    if not success:
                        print(f"[❌] Final failure: {game}")
                
                # Append retry results
                if buffer_retry_round:
                    round_sheet.append_rows(buffer_retry_round)
                if buffer_retry_singleplay:
                    singleplay_sheet.append_rows(buffer_retry_singleplay)
                
                # Re-run comparisons
                compare_results(round_sheet, f"Result Round Based ({currency})", 
                              ref_mapping_table, room_map, room_suffixes, special_three_lobby)
                compare_results(singleplay_sheet, f"Result Singleplay ({currency})", 
                              ref_mapping_single, room_map, room_suffixes, special_three_lobby)
                
            except Exception as e:
                print(f"[❌] Retry error: {e}")
            finally:
                try:
                    driver.quit()
                except:
                    pass

    print("[✅] Script completed")