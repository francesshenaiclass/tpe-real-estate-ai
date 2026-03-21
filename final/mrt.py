import pandas as pd
import json
from pathlib import Path

# 1. 自動定位路徑
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "清洗後_臺北捷運車站出入口座標.csv"
JSON_OUTPUT = BASE_DIR / "mrt_stations.json"

try:
    # 2. 讀取並清洗資料
    # 使用 utf-8-sig 處理 Excel 可能產生的 BOM
    mrt_df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    mrt_df.columns = mrt_df.columns.str.strip()

    # 3. 欄位抓取與改名 (對接你最新確認的 '出入口名稱')
    mrt_list = mrt_df[['出入口名稱', '緯度', '經度']].rename(
        columns={'緯度': 'lat', '經度': 'lon'}
    ).to_dict(orient='records')

    # 4. 直接儲存成檔案，不再只是列印
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(mrt_list, f, ensure_ascii=False, indent=4)
        
    print(f"成功！JSON 檔案已儲存在：{JSON_OUTPUT} (O_O)")

except KeyError as e:
    print(f"欄位名稱錯誤：找不到 {e}。目前的欄位有：{mrt_df.columns.tolist()}")
except Exception as e:
    print(f"發生錯誤：{e}")