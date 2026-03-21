import pandas as pd
from sqlalchemy import create_engine
from sshtunnel import SSHTunnelForwarder
import urllib.parse
import os

# 1. 連線設定 (請再次確認資訊無誤)
SSH_HOST = 'dv108.aiturn.fun'
SSH_PORT = 8022
SSH_USER = 'layla'
SSH_PASS = 'Dv108@'

DB_USER = 'layla'
DB_PASS = 'Dv108@'
DB_NAME = 'db_realestate'

def download_and_verify():
    print("(°∀°) 嘗試建立隧道 (簡約模式)...")
    
    # 建立 SSH 隧道
    try:
        # 移除 look_for_keys 與 allow_agent，回歸基本參數
        with SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USER,
            ssh_password=SSH_PASS,
            remote_bind_address=('127.0.0.1', 3306)
        ) as tunnel:
            
            print(f"✅ 隧道建立成功！映射埠口: {tunnel.local_bind_port}")
            
            # 建立資料庫引擎
            safe_db_pass = urllib.parse.quote_plus(DB_PASS)
            # 💡 指向隧道映射出來的本地埠口
            db_url = f'mysql+pymysql://{DB_USER}:{safe_db_pass}@127.0.0.1:{tunnel.local_bind_port}/{DB_NAME}'
            engine = create_engine(db_url)
            
            # 2. 抓取資料 (只拿最新 20 筆)
            query = "SELECT * FROM house_prices_taipei ORDER BY id DESC LIMIT 20"
            
            print("🚀 正在從伺服器下載資料...")
            df_verify = pd.read_sql(query, con=engine)
            
            # 3. 儲存與預覽
            output_file = "check_my_data.csv"
            df_verify.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print("\n" + "="*40)
            print(f"✨ 成功下載！檔案：{output_file}")
            print(f"📊 已抓取最新 {len(df_verify)} 筆資料。")
            print("="*40)
            
            # 在終端機直接印出前兩筆，讓你立刻確認欄位對不對
            if not df_verify.empty:
                print("📝 資料範例 (前兩筆)：")
                print(df_verify[['id', 'district', 'total_price', 'unit_price', 'transaction_date']].head(2))
            
    except Exception as e:
        print(f"(;´д｀) 下載失敗。原因：{e}")
        print("💡 提示：如果依然顯示 SSH 建立失敗，請檢查網路連線或 SSH 密碼。")

if __name__ == "__main__":
    download_and_verify()