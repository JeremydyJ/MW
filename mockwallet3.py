from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import requests
import json
from datetime import datetime

class GameRoomAutomation:
    def __init__(self):
        self.username = "qa"
        self.password = "qapassword"
        self.login_url = "https://uatmw.kmgamesdev.net/"
        self.nickname = "Jeremyhkd"
        self.game_list = ["belangkai-2", "baccarat"]
        self.minbet_records = []

        # API config
        self.room_api_url = "https://m13.ns86.kingdomhall729.com/table/api/room_members.json"
        self.base_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Origin": "https://cdn.kingdomhall729.com",
            "Referer": "https://cdn.kingdomhall729.com/",
            "User-Agent": "Mozilla/5.0"
        }

        self.room_ids = [
            "5e145e43e8af890e844b4dee",
        ]


        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-insecure-localhost')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--ignore-certificate-errors")
        self.driver = webdriver.Chrome(seleniumwire_options={}, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def login_to_game(self):
        try:
            self.driver.get(self.login_url)
            print("[🧪] 页面加载中...")

            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter user name']"))).send_keys(self.username)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter password']"))).send_keys(self.password)
            self.wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
            print("[✅] 登录成功")

            self.wait.until(EC.url_contains("/LoginTestPlayer"))
            nickname_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Enter login name']")))
            nickname_input.clear()
            nickname_input.send_keys(self.nickname)
            self.wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
            print(f"[✅] 设置昵称为 {self.nickname}")

            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='search by game']")))
            print("[🎮] 游戏大厅加载完成")
            return True
        except Exception as e:
            print(f"[❌] 登录失败: {str(e)}")
            return False

    def wait_for_token(self):
        print("[⏳] 等待 /sync_balance 请求...")
        for i in range(10):
            time.sleep(1)
            for request in self.driver.requests:
                if "/api/players/sync_balance" in request.url and request.response:
                    return request.headers.get("x-authentication-token")
        return None

    def get_room_info(self, token, room_id, game):
        headers = {
            **self.base_headers,
            "x-authentication-token": token,
            "x-client-id": "c927a7f2a4db52d24940ff3ca83dd862",
            "game-identifier": game,
        }
        response = requests.post(self.room_api_url, headers=headers, json={"room_id": room_id})
        if response.status_code == 200:
            data = response.json()
            room = data.get("roomMember", {}).get("room", {})
            min_bet = room.get("minBet")
            print(f"[🏷️] Game: {game}, Room ID: {room_id}, MinBet: {min_bet}")
        else:
            print(f"[❌] 房间 {room_id} 请求失败, 状态码: {response.status_code}")

    def run(self):
        if not self.login_to_game():
            return
        for game in self.game_list:
            print(f"\n[🎮] 启动游戏：{game}")
            try:
                search = self.driver.find_element(By.XPATH, "//input[@placeholder='search by game']")
                search.clear()
                search.send_keys(game)
                time.sleep(1.5)
                buttons = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(text(), 'Launch')]")))
                self.driver.requests.clear()
                buttons[0].click()
                time.sleep(1)
                token = self.wait_for_token()
                if not token:
                    print(f"[❌] 无法提取 token，跳过游戏 {game}")
                    continue
                print(f"[🔐] 捕获 token: {token}")
                for room_id in self.room_ids:
                    self.get_room_info(token, room_id, game)
                    time.sleep(2)
            except Exception as e:
                print(f"[❌] 游戏 {game} 处理异常: {e}")
        self.driver.quit()

if __name__ == "__main__":
    automation = GameRoomAutomation()
    automation.run()
