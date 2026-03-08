import csv
import os

def generate_district_report(house_data):
    """
    將單筆房屋資料寫入對應區域的 CSV 檔案中。
    例如：大安區的資料就會存入 housing_output/大安區.csv
    """
    # 設定存放 CSV 的資料夾名稱
    base_dir = os.path.dirname(__file__)
    folder = os.path.join(base_dir, "housing_output")
    
    # 如果資料夾不存在，就自動建立一個
    if not os.path.exists(folder):
        os.makedirs(folder)

    # 用「區域」來當作檔名
    district_name = house_data['區域']
    file_name = f"{district_name}.csv"
    full_path = os.path.join(folder, file_name)

    # 定義 CSV 的欄位標題 (必須跟 crawler 打包的 Key 一致)
    keys = ["區域", "建案名稱", "地址", "價格", "類型", "屋齡", "總坪數", "實際坪數", "樓層", "規格", "車位"]
    
    # 檢查這個區域的 CSV 是否已經存在 (用來決定要不要寫入標題列)
    file_exists = os.path.isfile(full_path)

    # 開啟檔案，模式設定為 "a" (append，附加在最後面)
    with open(full_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        
        # 如果檔案是剛剛才創建的，先寫入第一行的標題
        if not file_exists:
            writer.writeheader()
            
        # 寫入這筆房屋資料
        writer.writerow(house_data)