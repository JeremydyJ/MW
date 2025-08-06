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

# ---------- 批量写入函数 ----------
def batch_append_rows(ws, headers, data):
    # 清除旧数据（从第二行开始）
    if data:
        col_end = chr(ord('A') + len(headers) - 1)
        ws.batch_clear([f"A2:{col_end}1000"])  # 清掉旧数据，但保留 header

    # 永远写 header（第 1 行）
    ws.update('A1', [headers])

    if not data:
        return

    # 分批写入数据（从第 2 行开始）
    max_batch_size = 500
    for i in range(0, len(data), max_batch_size):
        chunk = data[i:i + max_batch_size]
        start_row = i + 2
        end_row = start_row + len(chunk) - 1
        cell_range = f"A{start_row}:{chr(ord('A') + len(headers) - 1)}{end_row}"
        ws.batch_update([{'range': cell_range, 'values': chunk}])

# ---------- 游戏映射 ----------
turnbased_display_to_identifier = {
    "bai-buu": "bai-buu",
    "bai-cao": "bai-cao",
    "Pusoy": "Pusoy",
    "king-pok-deng": "king-pok-deng",
    "pai-kang": "pai-kang",
    "five-card-poker": "five-card-poker",
    "teen-patti": "teen-patti",
    "Blackjack": "blackjack",
    "Tongits": "tongits"
}

turnbased_game_list = list(turnbased_display_to_identifier.keys())

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

# ---------- 等待 token 函数 ----------
def wait_for_token_in_storage(driver, timeout=20):
    start_time = time.time()
    for i in range(timeout):
        local_storage = driver.execute_script("return JSON.stringify(window.localStorage);")
        session_storage = driver.execute_script("return JSON.stringify(window.sessionStorage);")
        all_storage = {**json.loads(local_storage), **json.loads(session_storage)}
        for k, v in all_storage.items():
            if "token" in k.lower() or "authentication" in k.lower():
                duration = round(time.time() - start_time, 2)
                print(f"[🧩] 获取 token 成功: key = {k}，耗时: {duration} 秒")  # 输出总耗时
                return v
        time.sleep(1)
    print("[❌] 超时未获取到 token")
    return None

# ---------- 请求游戏房间数据 ----------
def run_game_and_get_info(game_name, game_identifier, buffer, include_chips=False):
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
    time.sleep(15)

    token = wait_for_token_in_storage(driver)
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
                buffer.append(row)
    else:
        raise Exception(f"[❌] 请求失败: {response.status_code}, 内容: {response.text}")
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    print(f"[✅] 处理完成: {game_name}")

# ---------- Google Sheet ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
sheet_turnbased = gc.open_by_url(sheet_url).worksheet("turn-based(HKD)")
sheet_turnbased.clear()
sheet_turnbased.append_row(["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"])

# ---------- 对比函数 ----------
ref_doc = gc.open_by_url(ref_sheet_url)

# Turnbased 映射
# ---------- 映射表 ----------
ref_ws_turnbased = ref_doc.worksheet("M13 Turn Based")
ref_data_turnbased = ref_ws_turnbased.get_all_values()
ref_mapping_turnbased = {}
for row in ref_data_turnbased[1:]:
    game_id = row[0].strip().lower()
    hkd = row[5].strip() if len(row) > 5 else ""
    if '-' in hkd:
        try:
            min_val, max_val = map(float, hkd.split("-"))
            ref_mapping_turnbased[game_id] = {"min": min_val, "max": max_val}
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

room_map = {}

# 构建 room_map
for row in ref_data_turnbased[1:]:
    full_id = row[0].strip().lower()  # eg. "bai-cao-1"
    if '-' not in full_id:
        continue
    parts = full_id.rsplit("-", 1)
    if len(parts) != 2:
        continue
    game, index = parts
    if index.isdigit():
        room_name = f"Lobby {int(index)}"
        room_map[(game, room_name)] = full_id


def get_or_create_worksheet(spreadsheet, title):
    try:
        # 尝试严格查找
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        # 不严格匹配名称，防止大小写或空格错误
        for ws in spreadsheet.worksheets():
            if ws.title.strip().lower() == title.strip().lower():
                print(f"[ℹ️] 找到类似名为 {ws.title}")
                return ws
        # 没有匹配的，尝试创建
        print(f"[🆕] 创建新工作表: {title}")
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")


def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        for ws in spreadsheet.worksheets():
            if ws.title.strip().lower() == title.strip().lower():
                print(f"[ℹ️] 找到类似名为 {ws.title}")
                return ws
        print(f"[🆕] 创建新工作表: {title}")
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")

def compare_and_write_results(source_ws, result_sheet_name):
    result_ws = get_or_create_worksheet(source_ws.spreadsheet, result_sheet_name)

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
        if ref_key and ref_key in ref_mapping_turnbased:
            expected = ref_mapping_turnbased[ref_key]

            if minBet == expected['min'] and maxBet == expected['max']:
                status = "✅ PASS"
                remark = ""
            elif minBet == expected['min'] and maxBet != expected['max']:
                status = "✅ PASS"
                remark = f"⚠️ MaxBet mismatch: expected {expected['max']}"
            else:
                status = "❌ FAILED"
                remark = f"Expected min: {expected['min']}, max: {expected['max']}"

            rows.append([row['Game'], room, minBet, maxBet, expected['min'], expected['max'], status, remark])
        else:
            rows.append([row['Game'], room, minBet, maxBet, "N/A", "N/A", "❌ NO MAPPING", "-"])
    
    batch_append_rows(result_ws,
                      ["Game", "Room Name", "Actual minBet", "Actual maxBet", "Expected minBet", "Expected maxBet", "Status", "Remark"],
                      rows)

# ---------- 比对执行 ----------
compare_and_write_results(sheet_turnbased, "Result turnbased(HKD)")
buffer_turnbased = []

if __name__ == "__main__":
    retry_turnbased = []

    try:
        print("[🚦] 脚本开始运行")
        driver = create_driver()
        wait = WebDriverWait(driver, 20)
        login_and_set_nickname()

        # Turnbased Game
        for game in turnbased_game_list:
            try:
                identifier = turnbased_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, buffer_turnbased, include_chips=True)
            except Exception as e:
                print(f"[⚠️] Turnbased 游戏失败: {game}，加入重试队列。错误: {e}")
                retry_turnbased.append(game)
        batch_append_rows(sheet_turnbased, ["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"], buffer_turnbased)

        driver.quit()

        # ---------- 重试阶段 ----------
        if retry_turnbased:
            print(f"[🔁] 重试 turnbased 游戏： {retry_turnbased}")

        for game in retry_turnbased:
            try:
                print(f"\n============== 重试 turnbased 游戏: {game} ==============")
                driver = create_driver()
                wait = WebDriverWait(driver, 20)
                login_and_set_nickname()
                identifier = turnbased_display_to_identifier.get(game.lower(), game.lower())
                run_game_and_get_info(game, identifier, buffer_turnbased, include_chips=True)
                driver.quit()
            except Exception as e:
                print(f"[❌] Singleplay 重试失败: {game}，错误: {e}")
                try: driver.quit()
                except: pass

        print("[📊] 开始比对 Turnbased 结果...")
        compare_and_write_results(sheet_turnbased, "Result Turnbased(HKD)")


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
