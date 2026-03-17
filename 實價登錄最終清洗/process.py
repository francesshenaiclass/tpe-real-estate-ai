import pandas as pd
import os

def process_and_merge():
    # 1. 定義行政區（確保順序與截圖一致）
    districts = ["中山區", "中正區", "信義區", "內湖區", "北投區", 
                 "南港區", "士林區", "大同區", "大安區", "文山區", 
                 "松山區", "萬華區"]
    
    combined_list = []
    print("🚀 開始讀取 12 區 CSV 並執行資料清洗與 One-Hot Encoding...")

    for district in districts:
        filename = f"{district}_realprice.csv"
        
        if not os.path.exists(filename):
            print(f"⚠️ 找不到檔案: {filename}，跳過...")
            continue
            
        # 讀取各區原始資料
        df = pd.read_csv(filename, encoding="utf-8-sig")
        
        for _, item in df.iterrows():
            row = {}
            
            # --- 行政區 One-Hot Encoding ---
            for d in districts:
                row[f"行政區_{d}"] = 1 if d == district else 0
            
            # --- 房屋基本資訊與價格 ---
            row["建坪"] = item.get("landArea", 0)
            row["房屋總價"] = item.get("price", 0)
            row["單價"] = item.get("uprice", 0)
            
            # --- 格局 ---
            row["房"] = item.get("room", 0)
            row["廳"] = item.get("hall", 0)
            row["衛"] = item.get("bath", 0)
            
            # --- 其他屬性 ---
            # 判斷車位：如果有填寫且不為空則計為 1
            parking = str(item.get("parking", ""))
            row["車位數量"] = 1 if parking and parking != "nan" and parking != "無" else 0
            row["是否加蓋"] = 0 
            
            # --- 房屋類型 One-Hot Encoding ---
            style_str = str(item.get("style", ""))
            row["房屋類型_公寓"] = 1 if "公寓" in style_str else 0
            row["房屋類型_大樓"] = 1 if "大樓" in style_str else 0
            row["房屋類型_華廈"] = 1 if "華廈" in style_str else 0
            row["房屋類型_透天"] = 1 if "透天" in style_str else 0
            
            # --- 經緯度處理 ---
            # 從原始 CSV 中抓取 lat/lng，如果欄位名稱不同請調整這裡
            row["緯度"] = item.get("lat", "")
            row["經度"] = item.get("lon", "")
            
            # --- 新增：成交年月 (處理你剛加入的 dealYearMonth) ---
            # 這欄位可以保留原始格式，方便匯入 OAC 做時間序列分析
            row["成交年月"] = item.get("dealYearMonth", "")
            
            combined_list.append(row)
        
        print(f"✅ 已處理: {district} ({len(df)} 筆)")

    # 2. 轉換為 DataFrame 並輸出最終版
    if combined_list:
        final_df = pd.DataFrame(combined_list)
        
        # 輸出 CSV
        output_filename = "final_taipei_real_price.csv"
        final_df.to_csv(output_filename, index=False, encoding="utf-8-sig")
        
        print("\n" + "="*30)
        print(f"✨ 最終版 CSV 生成成功！")
        print(f"📂 檔案名稱: {output_filename}")
        print(f"📊 總資料筆數: {len(final_df)} 筆")
        print(f"💡 包含欄位: 行政區(12個)、建坪、價格、格局、房屋類型(4個)、經緯度、成交年月")
        print("="*30)
    else:
        print("❌ 錯誤：未偵測到任何可處理的資料。")

if __name__ == "__main__":
    process_and_merge()