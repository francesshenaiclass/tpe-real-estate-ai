import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from crawler import find_page_max, crawl_property_sales
from csv_writer import write_header_csv
from csv_writer import write_info_csv

# 建立資料夾存放csv
if not os.path.exists("result_csv"):
    os.makedirs("result_csv")

# 輸入各縣市資料
with open("cities.json", "r", encoding="utf-8") as f:
    cities = json.load(f)

options = Options()
options.add_argument("--incognito")
options.add_argument("--window-size=1920,1080")  # 固定視窗大小，避免元素定位錯誤
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

header = ['路段', '屋齡', '房屋類型', '建坪', '主建物/陽台', '格局', '樓層', '房屋總價(萬)', '車位']

for city in cities.keys():# 取出每一個縣市
    for district, zipcode in cities[city].items():# 取出每個縣市的行政區及郵遞區號

        file_path = f"result_csv/{district}.csv"
        write_header_csv(file_path, header)# 建立該行政區的csv並寫入標題

        url = f"https://www.sinyi.com.tw/buy/list/apartment-dalou-huaxia-flat-townhouse-villa-type/{city}/{zipcode}-zip/default-desc/1"
        page_max = find_page_max(driver, url)# 找出目前行政區網頁最大頁數

        for page in range(1, page_max+1):# 抓取每頁資料
            url = f"https://www.sinyi.com.tw/buy/list/apartment-dalou-huaxia-flat-townhouse-villa-type/{city}/{zipcode}-zip/default-desc/{page}"
            rows = crawl_property_sales(driver, url, city, district, page, page_max) # 爬蟲抓取每頁20筆資料並回傳list
            write_info_csv(file_path, rows)# 資料加入csv檔案

driver.quit()
