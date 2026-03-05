import csv
import os
import re

# 這裡要加上 , count，讓這個功能「願意接收」編號
def generate_individual_report(article_data, count):
    base_dir = os.path.dirname(__file__)
    folder = os.path.join(base_dir, "news_output")
    
    if not os.path.exists(folder):
        os.makedirs(folder)

    # 清理標題
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', article_data['title'])
    
    # 這裡加上 {count:03d}_，檔名就會變成 001_標題.csv
    file_name = f"{count:03d}_{safe_title}.csv"
    full_path = os.path.join(folder, file_name)

    keys = ["title", "content"]
    with open(full_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows([article_data])
    
    print(f"📄 已產出 CSV：{file_name}")