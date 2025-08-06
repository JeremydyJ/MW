from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import time
import requests
import json

# ---------- 配置项 ----------
username = "qa"
password = "qapassword"
nickname = "Jeremyhkd"
search_game_list = ["baccarat", "belangkai-2"]  # 多个游戏名
login_url = "https://uatmw.kmgamesdev.net/"
client_id = "c927a7f2a4db52d24940ff3ca83dd862"

# ---------- 浏览器配置 ----------
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 20)

def extract_token():
    """从 localStorage 或 sessionStorage 中提取 token"""
    local_storage = driver.execute_script("return JSON.stringify(window.localStorage);")
    session_storage = driver.execute_script("return JSON.stringify(window.sessionStorage);")
    all_storage = {**json.loads(local_storage), **json.loads(session_storage)}
    for k, v in all_storage.items():
        if "token" in k.lower() or "authentication" in k.lower():
            return v
    return None

def get_min_bet(token, game_name):
    """使用 token 请求 lobbies 接口，提取 minBet 信息"""
    parsed_url = urlparse(driver.current_url)
    lobbies_url = f"{parsed_url.scheme}://{parsed_url.netloc}/table/api/lobbies"

    headers = {
        "x-authentication-token": token,
        "x-client-id": client_id,
        "Content-Type": "application/json",
        "origin": "https://cdn.kingdomhall729.com",
        "referer": "https://cdn.kingdomhall729.com/"
    }

    response = requests.get(lobbies_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"[📋] {game_name} 房间信息：")
        for lobby in data.get("lobbies", []):
            name = lobby.get("name")
            min_bet = lobby.get("minBet")
            max_bet = lobby.get("maxBetTag")
            print(f" - {name} | minBet: {min_bet} | maxBetTag: {max_bet}")
    else:
        print(f"[⚠️] 获取 {game_name} 房间失败，状态码: {response.status_code}")

try:
    print("[🧪] 打开后台登录页...")
    driver.get(login_url)

    # Step 1: 登录后台
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter user name']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter password']"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print("[✅] 登录成功")

    # Step 2: 设置昵称
    wait.until(EC.url_contains("/LoginTestPlayer"))
    nickname_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter login name']")))
    nickname_input.clear()
    nickname_input.send_keys(nickname)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    print(f"[✅] 设置昵称为 {nickname}")

    for game in search_game_list:
        # Step 3: 搜索游戏（确保触发 input 事件）
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='search by game']")))
        search_box = driver.find_element(By.XPATH, "//input[@placeholder='search by game']")
        driver.execute_script("arguments[0].value = '';", search_box)
        time.sleep(1)

        search_js = f'''
            const input = document.querySelector("input[placeholder='search by game']");
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(input, "{game}");
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        '''
        driver.execute_script(search_js)
        print(f"[🎯] 搜索游戏: {game}")
        time.sleep(2)

        # Step 4: 启动游戏
        launch_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Launch')]")))
        launch_button.click()
        print(f"[🚀] 启动游戏：{game}")

        # Step 5: 切换到新窗口
        time.sleep(5)
        driver.switch_to.window(driver.window_handles[-1])
        print("[🪟] 已切换到游戏标签页")

        # Step 6: 提取 token 并请求 minBet
        print("[🔍] 检查 localStorage 和 sessionStorage 中的所有内容...")
        time.sleep(12)
        token = extract_token()
        if token:
            print(f"[🔐] 成功获取 {game} 的 token: {token}")
            get_min_bet(token, game)
        else:
            print(f"[❌] 无法获取 {game} 的 token")

        # Step 7: 关闭游戏标签页，返回后台页
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        print("[🔁] 返回后台页面")

except Exception as e:
    print(f"[❌] 出错: {e}")
finally:
    driver.quit()
    print("[⏹] 流程结束")
