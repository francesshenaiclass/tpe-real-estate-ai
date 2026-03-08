from crawler import get_housing_data
from report import generate_district_report

# 1. 台北市 12 區完整名單
districts_to_scrape = [
    "大安區"
]

# 🌟 新增：用來追蹤「目前是哪一區」、該區的「獨立計數器」，以及「總計數器」
current_district = ""
district_count = 1 
total_count = 0

print("正在啟動永慶房屋 12 區資料抓取...")
print("-" * 60)

# 2. 啟動爬蟲
for house in get_housing_data(districts_to_scrape):
    
    # 🌟 【換區偵測邏輯】
    # 如果抓回來的資料區域，跟我們紀錄的 current_district 不一樣，代表換區了！
    if house['區域'] != current_district:
        current_district = house['區域'] # 更新目前區域
        district_count = 1               # 將該區的計數器重置回 1
        print(f"\n開始寫入新區域資料：【{current_district}】")
        print("-" * 40)
    
    # 寫入 CSV (會自動按區域分檔)
    generate_district_report(house)

    # 顯示進度 (改為顯示該區的獨立計數器 district_count)
    print(f"✅ 已寫入 {current_district} 第 {district_count:04d} 筆：{house['建案名稱'][:15]}")
    
    # 計數器 +1
    district_count += 1
    total_count += 1

# 3. 結束報告
print("\n✨ 12 區所有頁面抓取與寫入完成！")
# 結束時顯示總共抓了多少筆
print(f"📊 總計共抓取：{total_count} 筆純淨房屋資料") 
print("📁 請去 housing_output 資料夾收取你的 12 份 CSV 戰利品！")