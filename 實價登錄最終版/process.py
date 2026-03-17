import pandas as pd
import os

def clean_room_logic(val, field_type):
    """
    根據欄位類型處理無隔間邏輯：
    - 如果是 '房'：0 或無隔間轉為 1
    - 如果是 '廳' 或 '衛'：0 或無隔間轉為 0
    """
    try:
        num = int(float(val))
        if num > 0:
            return num
        else:
            # 數值為 0 或負數時
            return 1 if field_type == "房" else 0
    except (ValueError, TypeError):
        # 數值為 "無隔間"、NaN 或其他文字時
        return 1 if field_type == "房" else 0

def process_and_merge():
    districts = ["中山區", "中正區", "信義區", "內湖區", "北投區", 
                 "南港區", "士林區", "大同區", "大安區", "文山區", 
                 "松山區", "萬華區"]

    combined_list = []
    print("🚀 開始執行資料清洗 (邏輯：無隔間 -> 1房0廳0衛)...")

    for district in districts:
        filename = f"{district}_實價登錄.csv"
        
        if not os.path.exists(filename):
            print(f"⚠️ 找不到檔案: {filename}，跳過...")
            continue

        df = pd.read_csv(filename, encoding="utf-8-sig")

        for _, item in df.iterrows():
            row = {}
            # --- 行政區 One-Hot Encoding ---
            for d in districts:
                row[f"行政區_{d}"] = 1 if d == district else 0

            # --- 房屋基本資訊與價格 ---
            row["建坪"] = item.get("建物坪數", 0)
            row["地坪"] = item.get("土地坪數", 0)
            row["房屋總價"] = item.get("成交總價(萬)", 0)
            row["單價"] = item.get("單價(萬/坪)", 0)

            # --- 格局修正邏輯 ---
            row["房"] = clean_room_logic(item.get("房", 0), "房")
            row["廳"] = clean_room_logic(item.get("廳", 0), "廳")
            row["衛"] = clean_room_logic(item.get("衛", 0), "衛")

            # --- 其他屬性 ---
            parking = str(item.get("車位", ""))
            row["是否有車位"] = 1 if "有" in parking or "車位" in parking else 0
            
            # --- 房屋類型 One-Hot Encoding ---
            style_str = str(item.get("型式", ""))
            row["房屋類型_公寓"] = 1 if "公寓" in style_str else 0
            row["房屋類型_大樓"] = 1 if "大樓" in style_str else 0
            row["房屋類型_華廈"] = 1 if "華廈" in style_str else 0
            row["房屋類型_透天"] = 1 if "透天" in style_str else 0

            # --- 經緯度與成交年月 ---
            row["緯度"] = item.get("lat", "")
            row["經度"] = item.get("lon", "")
            row["成交年月"] = item.get("成交年月", "")

            combined_list.append(row)
        
        print(f"✅ 已處理: {district} ({len(df)} 筆)")

    if combined_list:
        final_df = pd.DataFrame(combined_list)
        output_filename = "final_taipei_real_price.csv"
        final_df.to_csv(output_filename, index=False, encoding="utf-8-sig")

        print("\n" + "="*30)
        print(f"✨ 最終版 CSV 生成成功！")
        print(f"📂 檔案名稱: {output_filename}")
        print("💡 邏輯確認：無隔間資料已轉換為 1房/0廳/0衛")
        print("="*30)
    else:
        print("❌ 錯誤：未偵測到任何可處理的資料。")

if __name__ == "__main__":
    process_and_merge()