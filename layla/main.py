from crawler import get_housing_data
from report import generate_district_report

# 🌟 解除封印：正式換回台北市 12 區全名單
districts_to_scrape = [
     "大同區", "中山區", "松山區", "大安區", "萬華區", 
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區"
]

current_district = ""
district_count = 1 
total_count = 0

print("🚀 正在啟動永慶房屋全自動大爬蟲 (包含車位深度抓取)...")
print("⚠️ 因為會不斷開啟分頁，預計執行時間會非常長！")
print("⚠️ 請接上電源、關閉電腦休眠模式，並放著讓它自己跑！")
print("-" * 60)

# 啟動爬蟲
for house in get_housing_data(districts_to_scrape):
    
    # 【換區偵測邏輯】
    if house['區域'] != current_district:
        current_district = house['區域'] 
        district_count = 1               
        print(f"\n📂 開始寫入新區域資料：【{current_district}】")
        print("-" * 40)
    
    # 寫入 CSV
    generate_district_report(house)

    # 在終端機印出進度，讓你安心
    print(f"✅ 已寫入 {current_district} 第 {district_count:04d} 筆：{house['地址'][:15]}")
    
    # 計數器 +1
    district_count += 1
    total_count += 1

# 結束報告
print("\n✨ 所有 12 區頁面抓取與寫入完成！")
print(f"📊 總計共抓取純住宅：{total_count} 筆房屋資料") 
print("📁 請去 housing_output 資料夾收取你的 CSV 戰利品！")