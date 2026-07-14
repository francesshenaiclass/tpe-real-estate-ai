import random
import time
import re
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
            
            # 🌟 新增：專屬這個區域的「已爬取網址黑名單」
            seen_urls = set()
            
            while True:
                url = f"https://buy.yungching.com.tw/list/台北市-{district}_c/?pg={page}"
                driver.get(url)
                
                # 模擬真人延遲
                delay_time = random.uniform(8, 12)
                print(f"⏳ [模擬真人] 停留 {delay_time:.1f} 秒... (正在處理 {district} 第 {page} 頁)")
                time.sleep(delay_time)
                
                try:
                    WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.buy-item"))
            )
                except TimeoutException:
                    print(f"🏁 【{district}】載入超時或無物件，結束該區。")
                    break 

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
                        print(f"📊 【{district}】系統偵測到共 {max_page} 頁")
                    except Exception as e:
                        print(f"⚠️ 【{district}】無法抓取總頁數，預設為 1 頁")
                        max_page = 1
                
                items = driver.find_elements(By.CSS_SELECTOR, "li.buy-item")
                
                if len(items) == 0:
                    break
                
                for item in items:
                    try:
                        # ==========================================
                        # 🌟 第一關：提取網址與「防重複攔截」
                        # ==========================================
                        try:
                            detail_url = item.get_attribute("href")
                            if not detail_url:
                                detail_url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                        except:
                            continue # 如果連網址都找不到，直接放棄這個破圖卡片
                            
                        # 🚨 核心攔截器：如果網址已經在名單裡，立刻踢掉！
                        if detail_url in seen_urls:
                            continue
                            
                        # 把新網址加入黑名單
                        seen_urls.add(detail_url)
                        # ==========================================

                        # 1. 地址過濾
                        try:
                            address = item.find_element(By.CLASS_NAME, "address").text.strip()
                        except:
                            continue
                            
                        if district not in address:
                            continue
                            
                        # 2. 抓取類型 (剔除店面、商業大樓等)
                        try:
                            case_type = item.find_element(By.CLASS_NAME, "caseType").get_attribute("textContent").strip()
                        except:
                            case_type = "無資料"

                        exclude_types = ["車位", "土地", "其他", "店面", "商業大樓", "辦公商業大樓"]
                        if case_type in exclude_types:
                            continue
                            
                        # 3. 抓取其餘列表頁面欄位
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

                        # ==========================================
                        # 🚀 進入詳情頁抓取車位與經緯度 (包含滾動觸發)
                        # ==========================================
                        main_window = driver.current_window_handle
                        car_val = "0"
                        lat = "無資料"
                        lng = "無資料"
                        
                        try:
                            driver.execute_script(f"window.open('{detail_url}', '_blank');")
                            driver.switch_to.window(driver.window_handles[-1]) 
                            
                            # 等待網頁主體出現
                            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            
                            # 🌟 破關必殺技：模擬真人往下滾動畫面
                            driver.execute_script("window.scrollTo(0, 800);")
                            time.sleep(0.5)
                            driver.execute_script("window.scrollTo(0, 1500);")
                            time.sleep(0.5)
                            driver.execute_script("window.scrollTo(0, 2200);")
                            time.sleep(1) # 給 Angular 1 秒鐘把假網址換成真網址
                            
                            # --- 任務 A：抓取車位 ---
                            try:
                                div_elements = driver.find_elements(By.XPATH, "//div[contains(., '車位')]")
                                if div_elements:
                                    div_text = " ".join([d.text for d in div_elements])
                                    match_1 = re.search(r'車位.*?(\d+)\s*個', div_text)
                                    match_2 = re.search(r'(\d+)\s*個車位', div_text)
                                    
                                    if match_1:
                                        car_val = match_1.group(1)
                                    elif match_2:
                                        car_val = match_2.group(1)
                                    elif "車位" in div_text and "無車位" not in div_text:
                                        car_val = "1"
                            except Exception:
                                pass 
                                
                            # --- 任務 B：抓取經緯度 (街景按鈕網址萃取版) ---
                            try:
                                amenity_block = WebDriverWait(driver, 3).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "app-buy-amenity"))
                                )
                                street_btn = amenity_block.find_element(By.CSS_SELECTOR, "a.btn-street-view")
                                map_url = street_btn.get_attribute("href")
                                
                                if map_url and "q=" in map_url:
                                    q_match = re.search(r'q=([\d\.]+),([\d\.]+)', map_url)
                                    if q_match:
                                        lat = q_match.group(1)
                                        lng = q_match.group(2)
                            except Exception:
                                pass 
                                
                        except Exception as e:
                            pass 
                        finally:
                            try:
                                while len(driver.window_handles) > 1:
                                    driver.switch_to.window(driver.window_handles[-1])
                                    driver.close()
                                driver.switch_to.window(main_window)
                            except Exception:
                                pass
                        # ==========================================

                        house_data = {
                            "區域": district,
                            "地址": address,
                            "價格": price_text,
                            "類型": case_type,
                            "屋齡": age,
                            "總坪數": reg_area,
                            "實際坪數": main_area,
                            "樓層": floor_info,
                            "規格": room_info,
                            "車位": car_val,
                            "緯度": lat,
                            "經度": lng
                        }
                        
                        yield house_data
                        
                    except Exception as e:
                        try:
                            if len(driver.window_handles) > 1:
                                driver.switch_to.window(driver.window_handles[-1])
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                        except Exception:
                            pass
                        continue
                
                if page >= max_page:
                    print(f"🏁 【{district}】已爬取至最後一頁 (第 {max_page} 頁)，準備切換下一區！")
                    break 
                else:
                    page += 1 

            time.sleep(random.uniform(5, 10))

    finally:
        driver.quit()