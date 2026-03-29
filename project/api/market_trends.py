import os
import math
import pymysql
import pandas as pd
import urllib.parse  # 🚩 必須引入，用來處理密碼特殊字元
from sqlalchemy import create_engine
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/trends", tags=["市場趨勢分析"])

# 1. 🔍 強力路徑偵測：確保讀到 project/ 根目錄下的 .env
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# 2. 🛡️ 建立資料庫引擎 (修正版)
def get_engine():
    user = os.getenv("user")
    pswd = os.getenv("DB_PASSWORD") 
    host = os.getenv("host")
    port = os.getenv("port")
    db   = os.getenv("database")
    
    if not all([user, pswd, host, db]):
        raise Exception("❌ .env 讀取失敗，請確認檔案內容與位置！")

    # 🚩 核心修正：對密碼進行 URL 編碼
    # 這會把 "Localuser@123" 轉成 "Localuser%40123"
    safe_pswd = urllib.parse.quote_plus(pswd)

    # 組合連線字串：mysql+pymysql://使用者:編碼密碼@主機:埠口/資料庫
    connection_str = f"mysql+pymysql://{user}:{safe_pswd}@{host}:{port}/{db}"
    
    return create_engine(connection_str)

DISTRICTS = ["中正區","大同區","中山區","松山區","大安區","萬華區","信義區","士林區","北投區","內湖區","南港區","文山區"]

def clean_json(obj):
    """防止 NaN 或 Infinity 導致 JSON 500 錯誤"""
    if isinstance(obj, list): return [clean_json(i) for i in obj]
    if isinstance(obj, dict): return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
    return obj

@router.get("/health")
async def health():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/monthly-growth")
async def get_monthly_growth(district: str = Query(None)):
    try:
        engine = get_engine()
        # 注意：請確保你的 SQL 欄位名稱與資料表一致
        query = "SELECT district, transaction_date, total_price FROM house_prices_taipei2"
        df = pd.read_sql(query, engine)
        
        # 清洗行政區空格
        df["district"] = df["district"].astype(str).str.strip()
        
        # 解析民國年月 (例如 11502 -> 2026-02)
        def parse_ym(val):
            try:
                s = str(int(float(val)))
                if len(s) == 5: return f"{int(s[:3])+1911}-{s[3:]:>02}"
                if len(s) == 6: return f"{s[:4]}-{s[4:]}"
            except: pass
            return None

        df["年月"] = df["transaction_date"].apply(parse_ym)
        df = df[df["年月"].notna()]
        df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
        df = df[df["total_price"] > 0]

        def calc(sub_df):
            # 以年月分組取均價
            m = sub_df.groupby("年月")["total_price"].mean().reset_index().sort_values("年月")
            res = []
            for i, r in m.iterrows():
                # 計算月增率
                mom = None
                if i > 0:
                    prev = m.loc[i-1, 'total_price']
                    if prev != 0:
                        mom = round((r['total_price'] - prev) / prev * 100, 2)
                
                res.append({
                    "年月": r["年月"], 
                    "均總價": round(r["total_price"], 1), 
                    "月增率": mom # 第一個月會是 None，符合 JSON
                })
            return res

        if district:
            data = calc(df[df["district"] == district.strip()])
            return clean_json({"district": district, "data": data})
        
        # 跑 12 區的循環
        result = {d: calc(df[df["district"] == d]) for d in DISTRICTS}
        return clean_json({"unit": "萬", "districts": result})

    except Exception as e:
        import traceback
        print("======== API 500 ERROR TRACEBACK ========")
        print(traceback.format_exc())
        print("=========================================")
        raise HTTPException(status_code=500, detail=str(e))