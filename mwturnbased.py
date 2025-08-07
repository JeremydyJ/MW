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
password = "qa123456"
login_url = "https://uatmw.kmgamesdev.net/"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"
lobbies_url = "https://m13.ns86.kingdomhall729.com/table/api/lobbies"
sheet_url = "https://docs.google.com/spreadsheets/d/1Yq0uXVaYufwWk1h-9BrOlbcQ_LJdnzQ7MsTAErAf_zQ/edit"
ref_sheet_url = "https://docs.google.com/spreadsheets/d/1bRCqItJyoxecxHDXC-pwrAP-4ZXfHovdceA6RqhGg2A/edit"

# ---------- Google Sheet ----------
credentials = Credentials.from_service_account_file('credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_url(sheet_url)
nickname_ws = spreadsheet.worksheet("nickname")

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

# ---------- 工具函数 ----------
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

def build_ref_mapping_turnbased(ref_ws, currency_code):
    values = ref_ws.get_all_values()
    if len(values) < 2:
        raise Exception("❌ 表格数据不足")

    header = values[0]
    currency_col_indexes = [i for i, col in enumerate(header) if col.strip().upper() == currency_code]
    if not currency_col_indexes:
        raise Exception(f"❌ 找不到 '{currency_code}' 列")

    ref_mapping = {}
    for row in values[1:]:  # 从第 2 行开始
        game_id = row[0].strip().lower()
        for idx in currency_col_indexes:
            if len(row) <= idx:
                continue
            cell = row[idx].strip()
            if "-" not in cell:
                continue
            try:
                min_bet, max_bet = map(float, cell.split('-'))
                print(f"[✅] 选中 {currency_code} 值: {min_bet} ~ {max_bet} (来自 column index {idx})")
                ref_mapping[game_id] = {"min": min_bet, "max": max_bet}
                break
            except:
                continue

    if not ref_mapping:
        raise Exception(f"❌ 没找到符合条件的 '{currency_code}' 值")
    return ref_mapping

def build_room_map(ref_ws):
    values = ref_ws.get_all_values()
    room_map = {}
    for row in values[1:]:  # Skip header
        full_id = row[0].strip().lower()
        if '-' not in full_id:
            continue
        parts = full_id.rsplit("-", 1)
        if len(parts) != 2:
            continue
        game, index = parts
        if index.isdigit():
            room_name = f"Lobby {int(index)}"
            room_map[(game, room_name)] = full_id
    return room_map

def run_game_and_get_info(driver, wait, nickname, game_name, game_identifier, buffer):
    print(f"\n============== 处理 {nickname} 游戏: {game_name} ==============")
    try:
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
        time.sleep(15)

        token = wait_for_token_in_storage(driver)
        if not token:
            raise Exception("❌ 无法获取 token")
            
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
        if response.status_code != 200:
            raise Exception(f"[❌] 接口请求失败: {response.status_code}")

        data = response.json()
        seen = set()
        for lobby in data.get("lobbies", []):
            name = lobby.get("name", "未知房间")
            min_bet = lobby.get("minBet", "?")
            max_bet = lobby.get("maxBetTag", "?")
            chips = lobby.get("availableChipOptions", [])
            chips_str = ", ".join(map(str, chips))
            key = (name, min_bet, max_bet, chips_str)
            if key not in seen:
                seen.add(key)
                print(f" - {name} | minBet: {min_bet} | maxBet: {max_bet} | Chips: {chips_str}")
                buffer.append([game_name, name, min_bet, max_bet, chips_str])
        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return True
    except Exception as e:
        print(f"[❌] 失败: {game_name}, 错误: {e}")
        return False
    finally:
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except:
            pass

def compare_and_write_results(source_ws, result_sheet_name, ref_mapping, room_map):
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

        ref_key = room_map.get((game, room))
        if ref_key and ref_key in ref_mapping:
            expected = ref_mapping[ref_key]
            if minBet == expected['min'] and maxBet == expected['max']:
                status = "✅ PASS"
                remark = ""
            elif minBet == expected['min']:
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

# ---------- 主程序 ----------
if __name__ == "__main__":
    for row in nickname_ws.get_all_records():
        nickname = row.get("nickname", "").strip()
        currency = row.get("currency", "").strip().upper()
        if not nickname or not currency:
            continue
        print(f"\n======================= 👤 处理昵称: {nickname} ({currency}) =======================")
        
        try:
            # 获取参考数据
            ref_doc = gc.open_by_url(ref_sheet_url)
            ref_ws_turnbased = ref_doc.worksheet("M13 Turn Based")
            ref_mapping = build_ref_mapping_turnbased(ref_ws_turnbased, currency)
            room_map = build_room_map(ref_ws_turnbased)
            
            # 创建工作表
            turnbased_sheet = get_or_create_worksheet(spreadsheet, f"Turn-based ({currency})")
            result_sheet_name = f"Result Turnbased({currency})"
            buffer_turnbased = []
            retry_queue = []

            # 创建driver并登录
            driver = create_driver()
            wait = WebDriverWait(driver, 20)
            login_and_set_nickname(driver, wait, nickname)

            for game in turnbased_game_list:
                identifier = turnbased_display_to_identifier.get(game.lower(), game.lower())
                success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_turnbased)
                if not success:
                    retry_queue.append(game)

            # 写入数据
            batch_append_rows(turnbased_sheet, 
                            ["Game", "Room Name", "minBet", "maxBet", "availableChipOptions"], 
                            buffer_turnbased)
            
            # 比较结果
            compare_and_write_results(turnbased_sheet, result_sheet_name, ref_mapping, room_map)
            print(f"[✅] {nickname} ({currency}) 完成 ✅")
            
        except Exception as e:
            print(f"[❌] 处理 {nickname} ({currency}) 时出错: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass

        # 重试阶段
        if retry_queue:
            print(f"[🔁] 重试以下游戏: {retry_queue}")
            buffer_retry = []
            try:
                print(f"\n============== 重试 turnbased 游戏: {game} ==============")
                driver = create_driver()
                wait = WebDriverWait(driver, 20)
                login_and_set_nickname(driver, wait, nickname)
                
                for game in retry_queue:
                    identifier = turnbased_display_to_identifier.get(game.lower(), game.lower())
                    success = run_game_and_get_info(driver, wait, nickname, game, identifier, buffer_retry)
                    if not success:
                        print(f"[❌] 最终失败: {game}")

                # 追加重试成功的数据
                if buffer_retry:
                    turnbased_sheet.append_rows(buffer_retry)
                    # 重新比较结果
                    compare_and_write_results(turnbased_sheet, result_sheet_name, ref_mapping, room_map)
                    
            except Exception as e:
                print(f"[❌] 重试时出错: {e}")
            finally:
                try:
                    driver.quit()
                except:
                    pass

    print("[✅] 脚本结束")