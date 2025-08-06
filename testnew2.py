from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import json
import requests

# 1. 高级浏览器配置
options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=options)
driver.get("https://u13.kingmidasdev.net/portal")

# 2. 登录流程
WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.NAME, "user"))
).send_keys("jeremydythb" + Keys.RETURN)

# 3. 七重点击保障机制
def ultimate_click():
    btn_locator = (By.CSS_SELECTOR, "input.game-launch-btn[value='Heist']")
    
    try:
        # === 机制1：基础等待 ===
        btn = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(btn_locator)
        )
        
        # === 机制2：视觉准备 ===
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", btn)
        time.sleep(1)
        
        # === 机制3：元素状态验证 ===
        print(f"元素状态: 显示[{btn.is_displayed()}] 启用[{btn.is_enabled()}] 坐标[{btn.location}]")
        
        # === 机制4：多重点击方式 ===
        attempts = [
            lambda: btn.click(),  # 标准点击
            lambda: driver.execute_script("arguments[0].click();", btn),  # JS点击
            lambda: ActionChains(driver).move_to_element(btn).pause(1).click().perform(),  # 动作链
            lambda: btn.send_keys(Keys.RETURN)  # 键盘触发
        ]
        
        for i, attempt in enumerate(attempts, 1):
            try:
                attempt()
                print(f"✅ 点击方式{i}成功")
                return True
            except Exception as e:
                print(f"⚠️ 点击方式{i}失败: {str(e)}")
                
        
        # === 机制5：强制激活 ===
        driver.execute_script("""
            const btn = arguments[0];
            btn.removeAttribute('disabled');
            btn.classList.remove('disabled');
            btn.style.pointerEvents = 'auto';
        """, btn)
        btn.click()
        
    except Exception as e:
        print(f"❌ 终极点击失败: {str(e)}")
        driver.save_screenshot('ultimate_click_fail.png')
        return False

# 执行点击
if ultimate_click():
    print("🎉 成功触发游戏加载")
    # 处理可能的游戏界面
    time.sleep(5)
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[1])
        
    # 4. 获取API数据
    def get_api_chip_values():
        url = "https://u13.kingmidasdev.net/table/api/lobbies.json"
        headers = {
            "Accept": "*/*",
            "Game-Identifier": "heist",
            "Origin": "https://cdn.kingmidasdev.net",
            "Referer": "https://cdn.kingmidasdev.net/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5.1 Safari/605.1.15",
            "X-Authentication-Token": "0010293b95754b299a3cacb11722ebd1"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # 假设API返回的结构中包含min_chip和max_chip值
            # 你需要根据实际的API响应结构调整这里的路径
            min_chip = data.get('min_chip')  # 可能是不同的字段名
            max_chip = data.get('max_chip')  # 可能是不同的字段名
            
            print(f"API返回的筹码值 - 最小: {min_chip}, 最大: {max_chip}")
            return min_chip, max_chip
        except Exception as e:
            print(f"获取API数据失败: {str(e)}")
            return None, None
    
    # 5. 获取UI中的筹码值
    def get_ui_chip_values():
        try:
            # 等待筹码控件加载
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".chip-selector"))
            )
            
            # 获取最小筹码值 - 根据实际UI调整选择器
            min_chip_element = driver.find_element(By.CSS_SELECTOR, ".min-chip-value")
            min_chip = min_chip_element.text.strip()
            
            # 获取最大筹码值 - 根据实际UI调整选择器
            max_chip_element = driver.find_element(By.CSS_SELECTOR, ".max-chip-value")
            max_chip = max_chip_element.text.strip()
            
            print(f"UI显示的筹码值 - 最小: {min_chip}, 最大: {max_chip}")
            return min_chip, max_chip
        except Exception as e:
            print(f"获取UI筹码值失败: {str(e)}")
            driver.save_screenshot('chip_values_fail.png')
            return None, None
    
    # 获取并比较筹码值
    api_min, api_max = get_api_chip_values()
    ui_min, ui_max = get_ui_chip_values()
    
    if api_min and api_max and ui_min and ui_max:
        # 比较值是否匹配
        if api_min == ui_min and api_max == ui_max:
            print("✅ 筹码值匹配: UI显示与API响应一致")
        else:
            print(f"❌ 筹码值不匹配: API(min:{api_min}, max:{api_max}) vs UI(min:{ui_min}, max:{ui_max})")
    else:
        print("⚠️ 无法完成筹码值比较，数据获取不完整")
    
else:
    print("💥 所有点击方式均失败")

driver.quit()