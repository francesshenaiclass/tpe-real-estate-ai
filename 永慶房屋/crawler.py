import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def get_housing_data(districts):
    
    driver = webdriver.Chrome()
    
    try:
        for district in districts:
            page = 1 
            max_page = 1 
            
            while True:
                url = f"https://buy.yungching.com.tw/list/台北市-{district}_c/?pg={page}"
                driver.get(url)
                
                # 模擬真人延遲 (12~18秒浮動)
                delay_time = random.uniform(12, 18)
                print(f"停留 {delay_time:.1f} 秒... (正在處理 {district} 第 {page} 頁,總共 {max_page} 頁)")
                time.sleep(delay_time)
                
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li.buy-item"))
                    )
                except TimeoutException:
                    print(f"🏁 【{district}】載入超時或無物件，結束該區。")
                    break 

                # 動態抓取總頁數 (只在第 1 頁執行)
                if page == 1:
                    try:
                        pagination_items = driver.find_elements(By.CLASS_NAME, "paginationPageListItem")
                        page_numbers = []
                        for p_item in pagination_items:
                            p_text = p_item.get_attribute("textContent").strip()
                            if p_text.isdigit():
                                page_numbers.append(int(p_text))
                        
                        if page_numbers:
                            max_page = max(page_numbers)
                        print(f"{district}】系統偵測到共 {max_page} 頁")
                    except Exception as e:
                        print(f"{district}】無法抓取總頁數，預設為 1 頁")
                        max_page = 1
                
                items = driver.find_elements(By.CSS_SELECTOR, "li.buy-item")
                
                if len(items) == 0:
                    break
                
                for item in items:
                    try:
                        # 1. 地址過濾 (剔除跨區廣告)
                        address = item.find_element(By.CLASS_NAME, "address").text.strip()
                        if district not in address:
                            continue
                            
                        # 2. 抓取物件名稱與類型
                        case_name = item.find_element(By.CLASS_NAME, "caseName").get_attribute("textContent").strip()
                        try:
                            case_type = item.find_element(By.CLASS_NAME, "caseType").get_attribute("textContent").strip()
                        except:
                            case_type = "無資料"

                        # 剔除車位、土地、其他
                        if case_type in ["車位", "土地", "其他"]:
                            continue
                            
                        # 3. 抓取其餘所有欄位
                        try:
                            price_text = item.find_element(By.CLASS_NAME, "price").get_attribute("textContent").replace(",", "").strip()
                        except:
                            price_text = "無資料"
                            
                        age = "無資料"
                        case_info_spans = item.find_elements(By.CSS_SELECTOR, ".case-info span")
                        for span in case_info_spans:
                            span_text = span.get_attribute("textContent").strip()
                            if "年" in span_text:
                                age = span_text
                                break
                                
                        try:
                            reg_area = item.find_element(By.CSS_SELECTOR, ".case-info .regArea").get_attribute("textContent").strip()
                            if not reg_area: reg_area = "無資料"
                        except:
                            reg_area = "無資料"

                        try:
                            main_area = item.find_element(By.CSS_SELECTOR, ".case-info .mainArea").get_attribute("textContent").strip()
                            if not main_area: main_area = "無資料"
                        except:
                            main_area = "無資料"

                        try:
                            floor_info = item.find_element(By.CSS_SELECTOR, ".case-info .floor").get_attribute("textContent").strip()
                            if not floor_info: floor_info = "無資料"
                        except:
                            floor_info = "無資料"

                        try:
                            room_info = item.find_element(By.CSS_SELECTOR, ".case-info .room").get_attribute("textContent").strip()
                            if not room_info: room_info = "無資料"
                        except:
                            room_info = "無資料"

                        try:
                            item.find_element(By.CSS_SELECTOR, ".case-info .car")
                            car_val = "1"
                            price_display = f"{price_text} 萬 (含車位價)"
                        except:
                            car_val = "0"
                            price_display = f"{price_text} 萬"

                        # --- 將資料打包 ---
                        house_data = {
                            "區域": district,
                            "建案名稱": case_name,
                            "地址": address,
                            "價格": price_display,
                            "類型": case_type,
                            "屋齡": age,
                            "總坪數": reg_area,
                            "實際坪數": main_area,
                            "樓層": floor_info,
                            "規格": room_info,
                            "車位": car_val
                        }
                        
                        yield house_data
                        
                    except Exception as e:
                        continue
                
                # 判斷是否已經爬到最後一頁
                if page >= max_page:
                    print(f"【{district}】已爬取至最後一頁 (第 {max_page} 頁)，準備切換下一區！")
                    break 
                else:
                    page += 1 

            # 換區休息
            time.sleep(random.uniform(5, 10))

    finally:
        driver.quit()