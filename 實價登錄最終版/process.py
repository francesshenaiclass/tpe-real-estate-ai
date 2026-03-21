import pandas as pd
import os
import numpy as np
from scipy.spatial import KDTree

# 1. 設定檔案路徑
MRT_PATH = "/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/final/清洗後_臺北捷運車站出入口座標.csv"
OUTPUT_FILENAME = "maxfinal_taipei_real_price_.csv"

def clean_room_logic(val, field_type):
    try:
        num = int(float(val))
        if num > 0:
            return num
        return 1 if field_type == "房" else 0
    except (ValueError, TypeError):
        return 1 if field_type == "房" else 0

def process_and_merge():
    districts = ["中山區", "中正區", "信義區", "內湖區", "北投區", 
                 "南港區", "士林區", "大同區", "大安區", "文山區", 
                 "松山區", "萬華區"]

    if not os.path.exists(MRT_PATH):
        print(f"❌ 錯誤：找不到捷運站檔案 {MRT_PATH}")
        return
    
    mrt_df = pd.read_csv(MRT_PATH)
    try:
        mrt_coords = mrt_df[['緯度', '經度']].dropna().astype(float).values
        mrt_tree = KDTree(mrt_coords)
        print("📡 捷運座標索引建立成功")
    except KeyError:
        print("❌ 錯誤：捷運檔案中找不到 '緯度' 或 '經度' 欄位。")
        return

    combined_list = []
    print("🚀 開始執行資料清洗並生成「含 ID」的資料庫格式...")

    for district in districts:
        filename = f"{district}_實價登錄.csv"
        if not os.path.exists(filename):
            print(f"⚠️ 找不到檔案: {filename}，跳過...")
            continue

        df = pd.read_csv(filename, encoding="utf-8-sig")

        for _, item in df.iterrows():
            row = {}
            # --- 1. 核心定位資訊 ---
            row["district"] = district
            row["latitude"] = item.get("lat") if pd.notnull(item.get("lat")) else item.get("緯度")
            row["longitude"] = item.get("lon") if pd.notnull(item.get("lon")) else item.get("經度")

            # --- 2. 行政區 One-Hot Encoding ---
            dist_map = {
                "中山區": "dist_zhongshan", "中正區": "dist_zhongzheng", "信義區": "dist_xinyi",
                "內湖區": "dist_neihu", "北投區": "dist_beitou", "南港區": "dist_nangang",
                "士林區": "dist_shilin", "大同區": "dist_datong", "大安區": "dist_daan",
                "文山區": "dist_wenshan", "松山區": "dist_songshan", "萬華區": "dist_wanhua"
            }
            for d_name, d_col in dist_map.items():
                row[d_col] = 1 if d_name == district else 0

            # --- 3. 面積與價格 ---
            row["building_area"] = float(item.get("建物坪數", 0))
            row["land_area"] = float(item.get("土地坪數", 0))
            row["total_price"] = float(item.get("成交總價(萬)", 0))
            row["unit_price"] = float(item.get("單價(萬/坪)", 0))
            row["house_age"] = float(item.get("屋齡", 0))

            # --- 4. 格局與車位 ---
            row["has_parking"] = 1 if any(x in str(item.get("車位", "")) for x in ["有", "車位"]) else 0
            row["rooms"] = clean_room_logic(item.get("房", 0), "房")
            row["halls"] = clean_room_logic(item.get("廳", 0), "廳")
            row["bathrooms"] = clean_room_logic(item.get("衛", 0), "衛")

            # --- 5. 房屋類型 One-Hot ---
            style_str = str(item.get("型式", ""))
            row["type_apartment"] = 1 if "公寓" in style_str else 0
            row["type_building"] = 1 if "大樓" in style_str else 0
            row["type_mansion"] = 1 if "華廈" in style_str else 0
            row["type_house"] = 1 if "透天" in style_str else 0

            # --- 6. 時間與空間計算 ---
            row["transaction_date"] = int(pd.to_numeric(item.get("成交年月", 0), errors='coerce') or 0)
            
            if pd.notnull(row["latitude"]) and pd.notnull(row["longitude"]):
                try:
                    d_deg, _ = mrt_tree.query([float(row["latitude"]), float(row["longitude"])])
                    row["distance_to_mrt"] = int(d_deg * 111320)
                except:
                    row["distance_to_mrt"] = 0
            else:
                row["distance_to_mrt"] = 0

            combined_list.append(row)
        
        print(f"✅ 已完成: {district}")

    if combined_list:
        final_df = pd.DataFrame(combined_list)
        
        # 💡 在最前面插入 ID 欄位 (從 1 開始)
        final_df.insert(0, 'id', range(1, len(final_df) + 1))
        
        # 依照資料庫 DESCRIBE 的精確順序排列
        cols_order = [
            'id', 'district', 'latitude', 'longitude', 'dist_zhongshan', 'dist_zhongzheng',
            'dist_xinyi', 'dist_neihu', 'dist_beitou', 'dist_nangang', 'dist_shilin',
            'dist_datong', 'dist_daan', 'dist_wenshan', 'dist_songshan', 'dist_wanhua',
            'building_area', 'land_area', 'total_price', 'unit_price', 'house_age',
            'has_parking', 'rooms', 'halls', 'bathrooms', 'type_apartment', 
            'type_building', 'type_mansion', 'type_house', 'transaction_date', 'distance_to_mrt'
        ]
        
        # 補齊可能缺失的欄位並對齊順序
        for col in cols_order:
            if col not in final_df.columns:
                final_df[col] = 0
        
        final_df = final_df[cols_order]
        final_df.to_csv(OUTPUT_FILENAME, index=False, encoding="utf-8-sig")

        print("\n" + "="*40)
        print(f"✨ 任務達成！")
        print(f"📂 輸出檔案: {OUTPUT_FILENAME}")
        print(f"🆔 已自動生成遞增 ID 並放在首欄")
        print(f"📊 總筆數: {len(final_df)}")
        print("="*40)

if __name__ == "__main__":
    process_and_merge()