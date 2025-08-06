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
room_members_url = "https://uat.kmgamesdev.net/table/api/room_members"
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_url = "https://docs.google.com/spreadsheets/d/1WzCW2LIwMh6w3ds6DmBGnwkvWYUiYiDYl6_0nnATA4o/edit"

# ---------- Google Sheet ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
sheet_crash = gc.open_by_url(sheet_url).worksheet("Crash (HKD)")
ref_sheet = gc.open_by_url(ref_url).worksheet("M7 Sigma Crash Games")

# ---------- 构建 ref_mapping_crash ----------
def build_ref_mapping_crash(ref_ws):
    values = ref_ws.get_all_values()
    if len(values) < 2:
        raise Exception("❌ 表格数据不足")

    header = values[0]
    hkd_col_indexes = [i for i, col in enumerate(header) if col.strip().upper() == "HKD"]
    if not hkd_col_indexes:
        raise Exception("❌ 找不到 'HKD' 列")

    for row in values[1:]:  # 从第 2 行开始
        game_name = row[0].strip().lower()
        if game_name != "lobby 1":
            continue
        for idx in hkd_col_indexes:
            if len(row) <= idx:
                continue
            cell = row[idx].strip()
            if "-" not in cell:
                continue
            try:
                min_bet, max_bet = map(float, cell.split('-'))
                # ✅ 只选你要的 1.0 - 500.0
                if min_bet == 1.0 and max_bet == 500.0:
                    print(f"[✅] 选中 HKD 值: {min_bet} ~ {max_bet} (来自 column index {idx})")
                    return {"lobby 1": {"min": min_bet, "max": max_bet}}
            except:
                continue

    raise Exception("❌ 没找到符合条件的 'HKD' 值（1.0 - 500.0）")


ref_mapping_crash = build_ref_mapping_crash(ref_sheet)

# ---------- 自动构建 room_map ----------
def build_room_map_from_actual(sheet):
    records = sheet.get_all_records()
    room_map = {}
    for row in records:
        game = row["Game"].strip().lower()
        room = row["Room Name"].strip().lower().replace(" ", "")
        if room in ("room1", "room2"):
            room = "lobby 1"
        key = (game, room)
        ref_key = f"{game}-lobby 1"
        room_map[key] = ref_key
    return room_map

# ---------- 游戏映射 ----------
crash_display_to_identifier = {
    "Iron Dome": "iron-dome",
    "interstellar-run": "interstellar-run",
    "Elite aviator Club": "elite-aviator-club",
    "Toon Crash": "toon-crash",
}
crash_game_list = list(crash_display_to_identifier.keys())

# ---------- 批量写入 ----------
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

# ---------- Selenium 控制 ----------
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    return webdriver.Chrome(options=chrome_options)

def login_and_set_nickname():
    print("[🔪] 打开后台登录页...")
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter user name']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter password']"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.url_contains("/LoginTestPlayer"))
    nickname_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter login name']")))
    nickname_input.clear()
    nickname_input.send_keys(nickname)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print(f"[✅] 设置昵称为 {nickname}")

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

def run_game_and_get_info(game_name, game_identifier, buffer):
    print(f"\n============== 处理游戏: {game_name} ==============")
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
    print(f"[🎯] 搜索游戏: {game_name}")
    time.sleep(1.5)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Launch')]"))).click()
    print(f"[🚀] 启动游戏：{game_name}")
    time.sleep(5)
    driver.switch_to.window(driver.window_handles[-1])
    print("[🪟] 已切换到游戏标签页")
    token = wait_for_token_in_storage(driver)
    if not token:
        raise Exception("❌ 无法获取 token")
    headers = {
        "x-authentication-token": token,
        "x-client-id": client_id,
        "origin": "https://cdn.kingdomhall729.com",
        "referer": "https://cdn.kingdomhall729.com/",
        "game-identifier": game_identifier
    }
    print(f"[🔗] 请求房间成员信息: {room_members_url}")
    r = requests.get(room_members_url, headers=headers)
    if r.status_code != 200:
        raise Exception(f"[❌] 接口请求失败: {r.status_code}")
    data = r.json()
    room = data.get("roomMember", {}).get("room", {})
    name = room.get("name", "lobby 1")
    min_bet = room.get("minBet")
    max_bet = room.get("maxBet")
    chips = room.get("chipOptions", [])
    chip_str = ", ".join(map(str, chips))
    print(f" - {name} | min: {min_bet} | max: {max_bet} | chips: {chip_str}")
    buffer.append([game_name, name, min_bet, max_bet, chip_str])
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

# ---------- 比对 ----------
def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except:
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")
    
def compare_and_write_results(source_ws, result_sheet_name):
    result_ws = get_or_create_worksheet(source_ws.spreadsheet, result_sheet_name)
    pull_data = source_ws.get_all_records()
    expected = ref_mapping_crash.get("lobby 1")

    rows = []
    for row in pull_data:
        try:
            game = row['Game']
            room = row['Room Name']
            minBet = float(row['minBet'])
            maxBet = float(row['maxBet'])
        except:
            continue

        if expected:
            if minBet == expected['min'] and maxBet == expected['max']:
                status = "✅ PASS"
                remark = ""
            elif minBet == expected['min']:
                status = "✅ PASS"
                remark = f"⚠️ MaxBet mismatch: expected {expected['max']}"
            else:
                status = "❌ FAILED"
                remark = f"Expected min: {expected['min']}, max: {expected['max']}"
            rows.append([game, room, minBet, maxBet, expected['min'], expected['max'], status, remark])
        else:
            rows.append([game, room, minBet, maxBet, "N/A", "N/A", "❌ NO REF", "-"])

    batch_append_rows(result_ws, ["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status", "Remark"], rows)

# ---------- 主程序 ----------
if __name__ == "__main__":
    buffer_crash = []
    retry_crash = []
    try:
        print("[🚦] 启动脚本")
        driver = create_driver()
        wait = WebDriverWait(driver, 20)
        login_and_set_nickname()
        for game in crash_game_list:
            try:
                identifier = crash_display_to_identifier.get(game, game.lower())
                run_game_and_get_info(game, identifier, buffer_crash)
            except Exception as e:
                print(f"[⚠️] 加入重试队列: {game}, 错误: {e}")
                retry_crash.append(game)
        driver.quit()

        if retry_crash:
            print("[🔁] 开始重试...")
            for game in retry_crash:
                try:
                    driver = create_driver()
                    wait = WebDriverWait(driver, 20)
                    login_and_set_nickname()
                    identifier = crash_display_to_identifier.get(game, game.lower())
                    run_game_and_get_info(game, identifier, buffer_crash)
                    driver.quit()
                except Exception as e:
                    print(f"[❌] 重试失败: {game}, 错误: {e}")
                    try: driver.quit()
                    except: pass

        # ✅ 所有成功的数据（包含 retry 后成功）统一写入
        batch_append_rows(sheet_crash, ["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"], buffer_crash)

        print("[📊] 比对结果中...")
        compare_and_write_results(sheet_crash, "Result crash(HKD)")

    except Exception as e:
        print(f"[💥] 脚本错误: {e}")
        try: driver.quit()
        except: pass
    finally:
        print("[✅] 脚本结束")
