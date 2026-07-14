import pandas as pd
from sqlalchemy import create_engine
from sshtunnel import SSHTunnelForwarder
import urllib.parse
import os

# ════════════════════════════════════════════════
# 1. 連線設定 (請再次確認 SSH 與 DB 資訊)
# ════════════════════════════════════════════════
SSH_HOST = 'dv108.aiturn.fun'
SSH_PORT = 8022
SSH_USER = 'Layla'
SSH_PASS = 'Dv108@'

DB_USER = 'layla'
DB_PASS = 'Dv108@'
DB_NAME = 'db_realestate'
CSV_INPUT = "maxfinal_taipei_real_price_.csv"

RENAME_MAP = {
    '緯度': 'latitude', '經度': 'longitude',
    '行政區_中山區': 'dist_zhongshan', '行政區_中正區': 'dist_zhongzheng',
    '行政區_信義區': 'dist_xinyi', '行政區_內湖區': 'dist_neihu',
    '行政區_北投區': 'dist_beitou', '行政區_南港區': 'dist_nangang',
    '行政區_士林區': 'dist_shilin', '行政區_大同區': 'dist_datong',
    '行政區_大安區': 'dist_daan', '行政區_文山區': 'dist_wenshan',
    '行政區_松山區': 'dist_songshan', '行政區_萬華區': 'dist_wanhua',
    '建坪': 'building_area', '地坪': 'land_area',
    '房屋總價': 'total_price', '單價': 'unit_price',
    '屋齡': 'house_age', '是否有車位': 'has_parking',
    '房': 'rooms', '廳': 'halls', '衛': 'bathrooms',
    '房屋類型_公寓': 'type_apartment', '房屋類型_大樓': 'type_building',
    '房屋類型_華廈': 'type_mansion', '房屋類型_透天': 'type_house',
    '成交年月': 'transaction_date'
}

def run_pipeline():
    # A. 讀取與處理資料 (同之前邏輯)
    if not os.path.exists(CSV_INPUT):
        print(f"(>_<) 找不到 CSV 檔案")
        return
    
    df = pd.read_csv(CSV_INPUT)
    dist_cols = [c for c in df.columns if '行政區_' in c]
    def get_dist_name(row):
        for col in dist_cols:
            if row[col] == 1: return col.replace('行政區_', '')
        return "未知"
    df['district'] = df.apply(get_dist_name, axis=1)
    df_en = df.rename(columns=RENAME_MAP)
    
    final_cols = [
        'district', 'latitude', 'longitude', 'dist_zhongshan', 'dist_zhongzheng',
        'dist_xinyi', 'dist_neihu', 'dist_beitou', 'dist_nangang', 'dist_shilin',
        'dist_datong', 'dist_daan', 'dist_wenshan', 'dist_songshan', 'dist_wanhua',
        'building_area', 'land_area', 'total_price', 'unit_price', 'house_age',
        'has_parking', 'rooms', 'halls', 'bathrooms', 'type_apartment', 
        'type_building', 'type_mansion', 'type_house', 'transaction_date'
    ]
    df_final = df_en[final_cols].copy()

    # B. 建立 SSH 隧道並匯入
    print(f"(°∀°) 正在建立隧道透過 {SSH_HOST}:{SSH_PORT}...")
    
    with SSHTunnelForwarder(
        (SSH_HOST, SSH_PORT),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASS,
        remote_bind_address=('127.0.0.1', 3306) # 假設資料庫在伺服器內是 3306
    ) as tunnel:
        
        print(f"✅ 隧道已建立！本地映射至 127.0.0.1:{tunnel.local_bind_port}")
        
        # 指向隧道建立的本地埠口
        safe_db_pass = urllib.parse.quote_plus(DB_PASS)
        db_url = f'mysql+pymysql://{DB_USER}:{safe_db_pass}@127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}'
        engine = create_engine(db_url)
        
        try:
            print(f"🚀 正在透過隧道匯入 {len(df_final)} 筆資料...")
            df_final.to_sql('house_prices_taipei', con=engine, if_exists='append', index=False, chunksize=100)
            print("✨ 完成！資料已成功翻牆進入資料庫。 (ˇωˇ)")
        except Exception as e:
            print(f"(;´д｀) 隧道內匯入失敗：{e}")

if __name__ == "__main__":
    run_pipeline()