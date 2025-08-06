from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time

class GameTester:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
    
    def login(self):
        self.driver.get("https://u13.kingmidasdev.net/portal")
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.NAME, "user"))
            ).send_keys("jeremydythb" + Keys.RETURN)
            
            # 验证登录成功
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'jeremydythbtester01')]"))
            )
            return True
        except Exception as e:
            print(f"登录失败: {str(e)}")
            self.driver.save_screenshot('login_fail.png')
            return False
    
    def ultimate_click(self, game_name):
        btn_locator = (By.XPATH, f"//input[@class='game-launch-btn' and @value='{game_name}']")
        try:
            btn = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable(btn_locator)
            )
            
            # 可视化调试
            self.driver.execute_script(
                "arguments[0].style.boxShadow='0 0 10px 5px rgba(255,0,0,0.5)';", btn)
            
            # 四种点击方式
            attempts = [
                ("直接点击", lambda: btn.click()),
                ("JS点击", lambda: self.driver.execute_script("arguments[0].click();", btn)),
                ("动作链点击", lambda: ActionChains(self.driver).move_to_element(btn).pause(0.5).click().perform()),
                ("回车触发", lambda: btn.send_keys(Keys.RETURN))
            ]
            
            for name, attempt in attempts:
                try:
                    attempt()
                    print(f"✅ {game_name} - {name}成功")
                    return True
                except Exception as e:
                    print(f"⚠️ {game_name} - {name}失败: {str(e)}")
            
            return False
        except Exception as e:
            print(f"❌ {game_name} 点击流程失败: {str(e)}")
            self.driver.save_screenshot(f'{game_name}_fail.png')
            return False
    
    def test_games(self, games_list):
        if not self.login():
            return {}  # 返回空字典而不是False
        
        results = {}
        for game in games_list:
            print(f"\n=== 开始测试 {game} ===")
            if self.ultimate_click(game):
                # 验证游戏加载
                time.sleep(3)
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    results[game] = "新标签页打开成功"
                    # 返回游戏大厅
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                else:
                    results[game] = "当前页加载成功"
            else:
                results[game] = "点击失败"
        
        return results
    
    def close(self):
        self.driver.quit()

# 使用示例
if __name__ == "__main__":
    tester = GameTester()
    
    # 配置要测试的游戏列表
    games_to_test = [
        "Andar Bahar",
        "Heist",
        "Baccarat", 
        "Blackjack"
        # 添加更多游戏...
    ]
    
    try:
        results = tester.test_games(games_to_test)
        
        print("\n=== 测试结果汇总 ===")
        for game, status in results.items():
            print(f"{game.ljust(15)}: {status}")
            
    finally:
        tester.close()