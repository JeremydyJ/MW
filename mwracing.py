import json
import time
import requests
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- 游戏配置 ----------
username = "qa"
password = "qa123456"
login_url = "https://uatmw.kmgamesdev.net/"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"
lobbies_url = "https://uat.kmgamesdev.net/table/api/lobbies"
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_sheet_url = "https://docs.google.com/spreadsheets/d/1bRCqItJyoxecxHDXC-pwrAP-4ZXfHovdceA6RqhGg2A/edit"

racing_display_to_identifier = {
    "horse-racing": "horse-racing",
    "treadmill-racing": "treadmill-racing",
    "marble-racing": "marble-racing",
    "cock-fighting": "cock-fighting",
    "Animal Racing": "animal-racing",
}
racing_game_list = list(racing_display_to_identifier.keys())

# ---------- 授权 Google Sheet ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_url(sheet_url)
nickname_ws = spreadsheet.worksheet("nickname")

# ---------- 工具函数 ----------
def extract_lobby_label(room_name):
    if "lobby" in room_name.lower() and "- 1" in room_name.lower():
        return "下主选项 1"
    return None

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
    print("[🔐] 登录成功，设置昵称...")
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
                print(f"[🧩] 获取 token 成功: key = {k}，耗时: {duration} 秒")
                return v
        time.sleep(1)
    print("[❌] 超时未获取到 token")
    return None

def build_ref_mapping(currency_code):
    ref_doc = gc.open_by_url(ref_sheet_url)
    ref_ws = ref_doc.worksheet("M7 Racing Games")
    ref_data = ref_ws.get_all_values()
    currency_col = None
    for idx, val in enumerate(ref_data[0]):
        if val.strip().upper() == currency_code:
            currency_col = idx
            break
    if currency_col is None:
        raise ValueError(f"找不到币种列: {currency_code}")
    mapping = {}
    for row in ref_data[1:]:
        label = row[0].strip()
        if not label.startswith("下主选项"):
            continue
        val = row[currency_col].strip() if currency_col < len(row) else ""
        if "-" in val:
            try:
                min_val, max_val = map(float, val.split("-"))
                mapping[label] = {"min": min_val, "max": max_val}
            except:
                continue
    return mapping

def run_game_and_get_info(nickname, game_name, game_identifier, buffer, include_chips=False):
    print(f"\n============== 处理 {nickname} 游戏: {game_name} ==============")
    driver = create_driver()
    wait = WebDriverWait(driver, 20)
    try:
        login_and_set_nickname(driver, wait, nickname)
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='search by game']"))                        )
        driver.execute_script("arguments[0].value = '';", search_box)
        print(f"[🔍] 正在搜索游戏: {game_name}")
        time.sleep(0.5)

        set_value_js = f'''
            const input = arguments[0];
            const lastValue = input.value;
            input.value = "{game_name}";
            const event = new Event('input', {{ bubbles: true }});
            const tracker = input._valueTracker;
            if (tracker) tracker.setValue(lastValue);
            input.dispatchEvent(event);
        '''
        driver.execute_script(set_value_js, search_box)

        time.sleep(1.5)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Launch')]"))).click()
        print(f"[🚀] 正在启动游戏: {game_name}")
        time.sleep(4)
        driver.switch_to.window(driver.window_handles[-1])
        print(f"[🌐] 切换到游戏窗口: {game_name}")
        token = wait_for_token_in_storage(driver)
        if not token:
            print(f"[❌] 获取 token 失败: {game_name}")
            return False
        headers = {
            "x-authentication-token": token,
            "x-client-id": client_id,
            "origin": "https://cdn.kingdomhall729.com",
            "referer": "https://cdn.kingdomhall729.com/",
            "game-identifier": game_identifier
        }
        print(f"[🌐] 请求 lobbies API: {lobbies_url}")
        response = requests.get(lobbies_url, headers=headers)
        if response.status_code != 200:
            print(f"[❌] 请求失败: {nickname}, status={response.status_code}, body={response.text}")
            return False
        try:
            data = response.json()
        except:
            print("[❌] 返回非 JSON 格式")
            return False
        seen = set()
        for lobby in data.get("lobbies", []):
            name = lobby.get("name", "未知房间")
            min_bet = lobby.get("minBet", "?")
            max_bet = lobby.get("maxBet", "?")
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
        return True
    except Exception as e:
        print(f"[❌] 失败: {game_name}, 错误: {e}")
        return False
    finally:
        driver.quit()

def compare_and_write_results(source_ws, result_sheet_name, label_to_min_max):
    result_ws = get_or_create_worksheet(source_ws.spreadsheet, result_sheet_name)
    pull_data = source_ws.get_all_records()
    rows = []
    for row in pull_data:
        game = row['Game'].strip()
        room = row['Room Name'].strip()
        try:
            minBet = float(row['minBet'])
            maxBet = float(row['maxBet'])
        except:
            continue
        ref_key = extract_lobby_label(room)
        if ref_key and ref_key in label_to_min_max:
            expected = label_to_min_max[ref_key]
            if minBet == expected['min']:
                if maxBet == expected['max']:
                    status = "✅ PASS"
                    remark = ""
                else:
                    status = "✅ PASS"
                    remark = f"⚠️ MaxBet mismatch: expected {expected['max']}"
            else:
                status = "❌ FAILED"
                remark = f"minBet 不匹配（期望: {expected['min']}）"
            rows.append([game, room, minBet, maxBet, expected['min'], expected['max'], status, remark])
        else:
            rows.append([game, room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING", "无对应 mapping"])
    batch_append_rows(result_ws,
        ["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status", "Remark"],
        rows)

# ---------- 主程序 ----------
if __name__ == "__main__":
    for row in nickname_ws.get_all_records():
        nickname = row.get("nickname", "").strip()
        currency = row.get("currency", "").strip().upper()
        if not nickname or not currency:
            continue
        print(f"\n======================= 👤 处理昵称: {nickname} ({currency}) =======================")
        racing_sheet = get_or_create_worksheet(spreadsheet, f"Racing ({currency})")
        result_sheet_name = f"Result racing({currency})"
        buffer_racing = []
        retry_queue = []
        ref_mapping = build_ref_mapping(currency)

        for game in racing_game_list:
            identifier = racing_display_to_identifier.get(game, game.lower())
            success = run_game_and_get_info(nickname, game, identifier, buffer_racing, include_chips=True)
            if not success:
                retry_queue.append(game)

        if retry_queue:
            print(f"[🔁] 重试以下游戏: {retry_queue}")
            for game in retry_queue:
                print(f"\n============== 重试游戏: {game} ==============")
                identifier = racing_display_to_identifier.get(game, game.lower())
                success = run_game_and_get_info(nickname, game, identifier, buffer_racing, include_chips=True)
                if not success:
                    print(f"[❌] 最终失败: {game}")

        batch_append_rows(racing_sheet, ["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"], buffer_racing)
        compare_and_write_results(racing_sheet, result_sheet_name, ref_mapping)
        print(f"[✅] {nickname} ({currency}) 完成 ✅")
