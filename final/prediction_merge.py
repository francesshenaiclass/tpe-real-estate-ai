import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus 
from dotenv import load_dotenv
import os

load_dotenv()
# 1. 設定資料庫連線資訊
DB_SETTINGS = DB_SETTINGS = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),  # 第二個參數是預設值
    "port": int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_NAME")
}

# 關鍵處理：對密碼進行編碼，防止 @ 符號破壞連線字串格式
safe_password = quote_plus(DB_SETTINGS['password'])

# 建立 SQLAlchemy Engine (使用編碼後的密碼)
engine = create_engine(
    f"mysql+pymysql://{DB_SETTINGS['user']}:{safe_password}@{DB_SETTINGS['host']}:{DB_SETTINGS['port']}/{DB_SETTINGS['database']}"
)

# 2. 欄位映射字典 (保持不變)
COLUMN_MAPPING = {
    '行政區': 'district', '路段': 'street', '緯度': 'latitude', '經度': 'longitude',
    '行政區_中山區': 'dist_zhongshan', '行政區_中正區': 'dist_zhongzheng', '行政區_信義區': 'dist_xinyi',
    '行政區_內湖區': 'dist_neihu', '行政區_北投區': 'dist_beitou', '行政區_南港區': 'dist_nangang',
    '行政區_士林區': 'dist_shilin', '行政區_大同區': 'dist_datong', '行政區_大安區': 'dist_daan',
    '行政區_文山區': 'dist_wenshan', '行政區_松山區': 'dist_songshan', '行政區_萬華區': 'dist_wanhua',
    '屋齡': 'house_age', '建坪': 'building_area', '房屋總價(萬)': 'total_price', '車位': 'parking_space',
    '房': 'rooms', '廳': 'halls', '衛': 'bathrooms', '室': 'extra_rooms', '有加蓋': 'has_extended',
    '總樓層': 'total_floors', '起始樓層': 'start_floor', '最高樓層': 'max_floor', '物件涵蓋層數': 'floor_span',
    '房屋類型_公寓': 'type_apartment', '房屋類型_大樓': 'type_building', '房屋類型_套房': 'type_studio',
    '房屋類型_華廈': 'type_mansion', '房屋類型_透天': 'type_house'
}

def import_csv_to_db(file_path, source_name):
    # 檢查檔案是否存在
    if not os.path.exists(file_path):
        print(f"❌ 找不到檔案: {file_path}，請檢查檔名是否正確。")
        return

    print(f"\n🚀 正在匯入: {file_path} (來源: {source_name})")
    try:
        df = pd.read_csv(file_path)
        
        # A. 針對組員 C 修正單位 (元 -> 萬)
        if '房屋總價' in df.columns and '房屋總價(萬)' not in df.columns:
            df['房屋總價(萬)'] = df['房屋總價'] / 10000
            df = df.rename(columns={'車位數量': '車位', '是否加蓋': '有加蓋'})

        # B. 針對組員 A 補齊行政區欄位
        if '路段' in df.columns and '行政區' not in df.columns:
            df['行政區'] = df['路段'].str.extract(r'台北市(.*?[區])')
            
        # C. 欄位映射與清洗
        df_to_db = df.rename(columns=COLUMN_MAPPING)
        db_cols = [c for c in df_to_db.columns if c in COLUMN_MAPPING.values()]
        df_final = df_to_db[db_cols].copy()
        
        # 3. 寫入資料庫
        df_final.to_sql('house_prediction_data', con=engine, if_exists='append', index=False)
        
        # 4. 補貼 data_source 標籤 (標註 NULL 的資料)
        with engine.begin() as conn:
            query = text("UPDATE house_prediction_data SET data_source = :source WHERE data_source IS NULL")
            conn.execute(query, {"source": source_name})
            
        print(f"✅ 成功匯入 {len(df_final)} 筆資料至 MySQL！")

    except Exception as e:
        print(f"⚠️ 處理 {file_path} 時出錯: {e}")

# --- 主程式執行區 ---
if __name__ == "__main__":
    # 使用你目前真實存在的檔名
    import_csv_to_db('信義房屋.csv', '信義房屋')
    import_csv_to_db('永慶房屋.csv', '永慶房屋') 
    import_csv_to_db('住商不動產.csv', '住商不動產') 
    
    print("\n🏁 所有行政區資料整合完畢！")