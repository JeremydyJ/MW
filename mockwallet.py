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

# 游戏显示名 → game-identifier 映射
game_display_to_identifier = {
    "baccarat": "baccarat",
    "cash-rocket": "cash-rocket",
    "belangkai-2": "belangkai-2",
    "blackjack": "blackjack",
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
    "bicho": "bicho",
    "thai-hi-lo": "thai-hi-lo-2"
}
game_list = list(game_display_to_identifier.keys())

# ---------- 浏览器配置 ----------
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("headless")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

# ---------- Google Sheets 认证 ----------
credentials = Credentials.from_service_account_file(
    'credentials.json',  # 请替换为你自己的路径
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url(sheet_url).worksheet("Round Based Game/ Table Games (HKD)")
sheet.clear()
sheet.append_row(["Game", "Room Name", "minBet", "maxBet"])

# ---------- 登录并设置昵称 ----------
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

# ---------- 启动游戏并获取 minBet ----------
def run_game_and_get_minbet(game_name):
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
    game_identifier = game_display_to_identifier.get(game_name.lower(), game_name.lower())
    headers = {
        "x-authentication-token": token,
        "x-client-id": client_id,
        "Content-Type": "application/json",
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
            key = (name, min_bet, max_bet)
            if key not in seen:
                seen.add(key)
                print(f" - {name} | minBet: {min_bet} | maxBet: {max_bet}")
                sheet.append_row([game_name, name, min_bet, max_bet])
    else:
        print(f"[❌] 请求失败: {response.status_code}")
        print(f"响应内容: {response.text}")
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    print(f"[✅] 处理完成: {game_name}")

# ---------- 主流程 ----------
try:
    login_and_set_nickname()
    for game in game_list:
        run_game_and_get_minbet(game)
except Exception as e:
    print(f"[❌] 出错: {e}")
finally:
    driver.quit()
    print("[⏹] 流程结束")
