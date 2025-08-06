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

# ---------- 配置项 ----------
username = "qa"
password = "qapassword"
nickname = "Jeremyhkd"
login_url = "https://uatmw.kmgamesdev.net/"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"
lobbies_url = "https://m13.ns86.kingdomhall729.com/table/api/lobbies"
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_sheet_url = "https://docs.google.com/spreadsheets/d/1bRCqItJyoxecxHDXC-pwrAP-4ZXfHovdceA6RqhGg2A/edit"

# ---------- 游戏映射 ----------
round_display_to_identifier = {
    "baccarat": "baccarat",
    "cash-rocket": "cash-rocket",
    "belangkai-2": "belangkai-2",
    # "blackjack": "blackjack",
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
    # "bicho": "bicho",
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

# ---------- 创建 driver ----------
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("headless")
    chrome_options.add_argument("--start-maximized")
    return webdriver.Chrome(options=chrome_options)

# ---------- 登录函数 ----------
def login_and_set_nickname():
    print("[🔪] 打开后台登录页...")
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter user name']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter password']"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print("[✅] 登录成功")
    wait.until(EC.url_contains("/LoginTestPlayer"))
    nickname_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter login name']")))
    nickname_input.clear()
    nickname_input.send_keys(nickname)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print(f"[✅] 设置昵称为 {nickname}")

# ---------- 请求游戏房间数据 ----------
def run_game_and_get_info(game_name, game_identifier, sheet_target, include_chips=False):
    print(f"\n============== 处理游戏: {game_name} ==============")
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='search by game']")))
    search_box = driver.find_element(By.XPATH, "//input[@placeholder='search by game']")
    driver.execute_script("arguments[0].value = '';", search_box)
    time.sleep(1)
    search_js = f'''
        const input = document.querySelector("input[placeholder='search by game']");
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        nativeInputValueSetter.call(input, "{game_name}");
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
    '''
    driver.execute_script(search_js)
    print(f"[🎯] 搜索游戏: {game_name}")
    time.sleep(1.5)
    launch_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Launch')]")))
    launch_button.click()
    print(f"[🚀] 启动游戏：{game_name}")
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])
    print("[🪟] 已切换到游戏标签页")
    time.sleep(12)

    local_storage = driver.execute_script("return JSON.stringify(window.localStorage);")
    session_storage = driver.execute_script("return JSON.stringify(window.sessionStorage);")
    all_storage = {**json.loads(local_storage), **json.loads(session_storage)}
    token = None
    for k, v in all_storage.items():
        if "token" in k.lower() or "authentication" in k.lower():
            token = v
            break
    if not token:
        raise Exception(f"[❌] 无法获取 {game_name} 的 token")
    print(f"[🔐] 成功获取 token: {token}")

    headers = {
        "x-authentication-token": token,
        "x-client-id": client_id,
        "content-type": "application/json",
        "origin": "https://cdn.kingdomhall729.com",
        "referer": "https://cdn.kingdomhall729.com/",
        "game-identifier": game_identifier
    }

    print(f"[🌐] 请求 lobbies 接口: {lobbies_url}")
    response = requests.get(lobbies_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        seen = set()
        for lobby in data.get("lobbies", []):
            name = lobby.get("name", "未知房间")
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
                sheet_target.append_row(row)
    else:
        raise Exception(f"[❌] 请求失败: {response.status_code}, 内容: {response.text}")
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    print(f"[✅] 处理完成: {game_name}")

# ---------- Google Sheet ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
sheet_round = gc.open_by_url(sheet_url).worksheet("testing")
sheet_singleplay = gc.open_by_url(sheet_url).worksheet("test2")
# sheet_round.clear()
sheet_round.append_row(["Game", "Room Name", "minBet", "maxBet"])
# sheet_singleplay.clear()
sheet_singleplay.append_row(["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"])

# ---------- 对比函数 ----------
ref_doc = gc.open_by_url(ref_sheet_url)

# Singleplay 映射
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

# Table Game 映射
ref_ws_table = ref_doc.worksheet("M13 Table Games")
ref_data_table = ref_ws_table.get_all_values()
ref_mapping_table = {}
for row in ref_data_table[1:]:
    key = row[0].strip().lower()  # 直接是 table-games-casual 等
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

# ---------- 构建 Table Game 映射 ----------
room_suffixes = {
    "Casual": "table-games-casual",
    "Novice": "table-games-novice",
    "Expert": "table-games-expert",
    "High Roller": "table-games-high-roller",
    "Lobby 1": "table-games-lobby-1"
}

table_game_list = [
    "baccarat", "cash-rocket", "belangkai-2", "blackjack", "colour game mega bonus",
    "color-game", "andar-bahar", "andar-bahar-2", "teen patti blitz", "dice duet",
    "thirty-two-cards", "dragon-tiger-2", "sicbo", "jhandi-munda", "thai-fish-prawn-crab",
    "fruit-roulette", "fan-tan-3", "viet-fish-prawn-crab", "xoc-dia-2", "ladder game",
    "monkey-king-roulette", "seven-up-down", "bola-golek", "bonus-dice", "coin-toss",
    "jogo-de-bozo", "bicho", "thai-hi-lo"
]

table_game_room_map = {}
for game in table_game_list:
    for room, suffix in room_suffixes.items():
        table_game_room_map[(game, room)] = f"{game}-{suffix}"

# 例外游戏：cash-rocket 特殊编号映射
table_game_room_map.update({
    ("cash-rocket", "Casual"): "cash-rocket-1",
    ("cash-rocket", "Novice"): "cash-rocket-2",
    ("cash-rocket", "Expert"): "cash-rocket-3",
    ("cash-rocket", "High Roller"): "cash-rocket-4"
})


def compare_and_write_results(source_ws, result_sheet_name):
    pull_data = source_ws.get_all_records()
    try:
        result_ws = source_ws.spreadsheet.worksheet(result_sheet_name)
        # result_ws.clear()
    except:
        result_ws = source_ws.spreadsheet.add_worksheet(title=result_sheet_name, rows="100", cols="10")

    result_ws.append_row(["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status"])

    for row in pull_data:
        game = row['Game'].strip().lower()
        room = row['Room Name'].strip()
        minBet = float(row['minBet'])
        maxBet = float(row['maxBet'])

        ref_key = room_map.get((game, room))
        if ref_key and ref_key in ref_mapping_single:
            expected = ref_mapping_single[ref_key]
            status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
            result_ws.append_row([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
        else:
            result_ws.append_row([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING"])

def compare_table_game_results(source_ws, result_sheet_name):
    pull_data = source_ws.get_all_records()
    try:
        result_ws = source_ws.spreadsheet.worksheet(result_sheet_name)
        # result_ws.clear()
    except:
        result_ws = source_ws.spreadsheet.add_worksheet(title=result_sheet_name, rows="100", cols="10")

    result_ws.append_row(["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status"])

    for row in pull_data:
        game = row['Game'].strip().lower()
        room = row['Room Name'].strip()
        minBet = float(row['minBet'])
        maxBet = float(row['maxBet'])

        # ✅ 优先使用特殊映射（如 cash-rocket）
        special_key = table_game_room_map.get((game, room))
        if special_key and special_key in ref_mapping_table:
            expected = ref_mapping_table[special_key]
            status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
            result_ws.append_row([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
        else:
            # ✅ 否则 fallback 使用 roomSuffix，如 table-games-casual
            ref_key = room_suffixes.get(room)
            if ref_key and ref_key in ref_mapping_table:
                expected = ref_mapping_table[ref_key]
                status = "✅ PASS" if minBet == expected['min'] and maxBet == expected['max'] else "❌ FAILED"
                result_ws.append_row([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status])
            else:
                result_ws.append_row([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING"])



# ---------- 比对执行 ----------
compare_and_write_results(sheet_singleplay, "Result singleplay(HKD)")
if __name__ == "__main__":
    retry_round = []
    retry_singleplay = []

    try:
        print("[🚦] 脚本开始运行")
        driver = create_driver()
        wait = WebDriverWait(driver, 20)
        login_and_set_nickname()

        # Round Game（可注释）
        for game in round_game_list:
            try:
                identifier = round_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, sheet_round)
            except Exception as e:
                print(f"[⚠️] Round 游戏失败: {game}，加入重试队列。错误: {e}")
                retry_round.append(game)

        # Singleplay Game
        for game in singleplay_game_list:
            try:
                identifier = singleplay_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, sheet_singleplay, include_chips=True)
            except Exception as e:
                print(f"[⚠️] Singleplay 游戏失败: {game}，加入重试队列。错误: {e}")
                retry_singleplay.append(game)

        driver.quit()

        # ---------- 重试阶段 ----------
        if retry_round or retry_singleplay:
            print(f"\n[🔁] 重试 Round 游戏： {retry_round}")
            print(f"[🔁] 重试 Singleplay 游戏： {retry_singleplay}")

        for game in retry_round:
            try:
                print(f"\n============== 重试 Round 游戏: {game} ==============")
                driver = create_driver()
                wait = WebDriverWait(driver, 20)
                login_and_set_nickname()
                identifier = round_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, sheet_round)
                driver.quit()
            except Exception as e:
                print(f"[❌] Round 重试失败: {game}，错误: {e}")
                try: driver.quit()
                except: pass

        for game in retry_singleplay:
            try:
                print(f"\n============== 重试 Singleplay 游戏: {game} ==============")
                driver = create_driver()
                wait = WebDriverWait(driver, 20)
                login_and_set_nickname()
                identifier = singleplay_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, sheet_singleplay, include_chips=True)
                driver.quit()
            except Exception as e:
                print(f"[❌] Singleplay 重试失败: {game}，错误: {e}")
                try: driver.quit()
                except: pass

        print("[📊] 开始比对 Singleplay 结果...")
        compare_and_write_results(sheet_singleplay, "Result singleplay(HKD)")

        print("[📊] 开始比对 Round Based Game / Table Games 结果...")
        compare_table_game_results(sheet_round, "Result Round Based Game/ Table Games (HKD)")

    except KeyboardInterrupt:
        print("[⛔️] 用户中断脚本")
        try: driver.quit()
        except: pass

    except Exception as e:
        print(f"[❌] 脚本出错: {e}")
        try: driver.quit()
        except: pass

    finally:
        print("[✅] 脚本结束")
