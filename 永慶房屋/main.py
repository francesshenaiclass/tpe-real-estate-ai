from crawler import get_news_data
from report import generate_individual_report

# 1. 啟動爬蟲
print("🚀 正在抓取新聞並同步存入 CSV 與 XAMPP 資料庫...")

count = 1 

for article in get_news_data(pages=3):
    # 這裡遞出 2 個東西：文章內容 (article) 和 編號 (count)
    generate_individual_report(article, count)


    print(f"✅ 已處理第 {count} 篇：{article['title'][:15]}...")
    count += 1

print("\n✨ 抓取完成！")
print(f"📊 總計抓取：{count - 1} 篇文章")
print("📁 CSV 存放在：news_output 資料夾")
print("🌐 資料已存入 XAMPP MySQL 資料庫！")