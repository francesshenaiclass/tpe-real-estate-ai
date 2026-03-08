from selenium import webdriver  
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import logging
import os
from datetime import datetime
import re
import requests

# 建立 logs 資料夾
if not os.path.exists("logs"):
    os.makedirs("logs")

log_filename = datetime.now().strftime("logs/crawler_%Y%m%d_%H%M%S.log")

#設定logging
logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),  # 保存到檔案
        logging.StreamHandler()  # 同時輸出到 console
    ]
)

# 抓網站頁數
def find_page_max(driver, url):
    page_max = 0
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "pagination_pageLinkClassName__d_GP1"))
        )

        # 取得目前網址
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        pages = soup.find_all("a",  class_="pagination_pageLinkClassName__d_GP1")

        for page in pages:
            num = int(page.text)
            if num > page_max:
                page_max = num

    except Exception as e:
        logging.error(f"抓取頁數失敗: {e}")

    return page_max


# 抓房屋出售資訊
def crawl_property_sales(driver, url, city, district, page, page_max):
    content_rows = []
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "longInfoCard_LongInfoCard_TypeWeb__LmDO7"))
            )

        # 取得目前網址
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        blocks = soup.find_all("div", id=lambda x: x and x.startswith("buyHouseCard_"))

        logging.info(f"正在處理 {city}-{district}, 第 {page}/{page_max} 頁, 抓到 {len(blocks)} 筆")

        for block in blocks:
            try:
                div0 = block.find("div", class_="longInfoCard_LongInfoCard_TypeWeb__LmDO7")
                div = div0.find("div", class_="longInfoCard_LongInfoCard_Type_Address__vAR4P LongInfoCard_Type_Address")
                # 找到裡面所有 span
                spans = div.find_all("span")
                # 用索引分別取出三個值
                road = spans[0].get_text(strip=True)   # 路段
                age = spans[1].get_text(strip=True)    # 屋齡
                house_type = spans[2].get_text(strip=True)  # 房屋類型
                div2 = div0.find("div", class_ = "longInfoCard_LongInfoCard_Type_HouseInfo__tZXDa")
                spans = div2.find_all("span")

                # 用索引分別取出四個值
                gfa = spans[0].get_text(strip=True)   # 建坪 Gross Floor Area
                psb = spans[1].get_text(strip=True)    # 主建物/陽台 Primary Structure  /Balcony
                layout = spans[2].get_text(strip=True)  # 格局
                floor = spans[3].get_text(strip=True)  # 樓層
                span = div0.find("span", style = "font-size: 1.75em; font-weight: 500; color: rgb(221, 37, 37);")
                total_price = span.get_text(strip=True) #房屋總售價

                div3 = div0.find("div", class_ = "LongInfoCard_Type_Right")
                # 找出 div 裡所有 span

                parking_space = "0"
                spans = div3.find_all("span")
                for span in spans:
                    text = span.get_text()
                    if "(含車位價)" in text:
                        link = f"https://www.sinyi.com.tw{block.find('a')['href']}"
                        
                        driver.get(link)
                        # 找到 span 標籤
                        span = driver.find_element("css selector", "span.buy_parking-info__mP8a5")
                        text = span.text.strip()
                        # 用正則抓第一個數字
                        first_number = re.search(r'\d+', text).group()
                        parking_space = first_number

                content_rows.append([road, age, house_type, gfa, psb, layout, floor, total_price, parking_space])
            
            except Exception as e:
                logging.warning(f"解析某筆房屋資料失敗: {e}")

    except Exception as e:
        logging.error(f"抓取 {city}-{district} 第 {page} 頁失敗: {e}")

    return content_rows

