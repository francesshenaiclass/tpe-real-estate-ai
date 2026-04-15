import os
import math
import pymysql
import pandas as pd
import urllib.parse
from sqlalchemy import create_engine
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter(prefix="/api/trends", tags=["市場趨勢分析"])

# ════════════════════════════════════════════════
# 1. 系統初始化與資料庫配置
# ════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

def get_engine():
    """
    建立資料庫連線引擎。
    - 支援特殊字元密碼轉碼 (urllib.parse)。
    - 從環境變數 (.env) 讀取敏感資訊，確保雲端與本地部署安全性。
    """
    user = os.getenv("user")
    pswd = os.getenv("DB_PASSWORD") 
    host = os.getenv("host")
    port = os.getenv("port")
    db   = os.getenv("database")
    
    if not all([user, pswd, host, db]):
        raise Exception("❌ .env 讀取失敗，請確認檔案內容與位置！")

    safe_pswd = urllib.parse.quote_plus(pswd)
    connection_str = f"mysql+pymysql://{user}:{safe_pswd}@{host}:{port}/{db}"
    return create_engine(connection_str)

DISTRICTS = ["中正區","大同區","中山區","松山區","大安區","萬華區","信義區","士林區","北投區","內湖區","南港區","文山區"]

def clean_json(obj):
    """
    資料清洗輔助函式。
    - 解決 Pandas 運算後產生的 NaN 或 Infinity 無法轉為 JSON 的問題。
    - 確保 API 回傳 100% 符合 JSON 標準。
    """
    if isinstance(obj, list): return [clean_json(i) for i in obj]
    if isinstance(obj, dict): return {k: clean_json(v) for k, v in obj.items()}
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
    return obj

# ════════════════════════════════════════════════
# 2. API 端點
# ════════════════════════════════════════════════

@router.get("/health", summary="系統健康檢查")
async def health():
    """
    ## 系統狀態監控：
    - 檢查 FastAPI 伺服器是否正常運作。
    - 測試與 MySQL 資料庫 (包含 GCP 雲端備援) 的連線狀態。
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return {"status": "ok", "db": "connected", "mode": "production"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/monthly-growth", summary="獲取各區房價月增率趨勢")
async def get_monthly_growth(
    district: Optional[str] = Query(None, description="行政區名稱，若不填則回傳全台北市各區資料", example="大安區")
):
    """
    ## 房價趨勢數據分析邏輯：
    1. **資料提取**：從 Dv108主機的資料庫提取 Table `house_prices_taipei2` 讀取實價登錄原始數據。
    2. **日期正規化**：將民國格式 (如 11502) 或特殊字串自動解析為 ISO 標準日期 (2026-02)。
    3. **時序聚合**：依據年月分組，計算該月份的「平均總價」。
    4. **指標運算 (MoM)**：計算每一月份相對於前一月份的 **月增率 (Month-over-Month)**。
    
    ### 回傳格式說明：
    - **年月**：YYYY-MM 格式。
    - **均總價**：該月成交平均價格 (萬元)。
    - **月增率**：相較上月的漲跌幅百分比 (%)。
    """
    try:
        engine = get_engine()
        # 從資料庫撈取原始交易紀錄
        query = "SELECT district, transaction_date, total_price FROM house_prices_taipei"
        df = pd.read_sql(query, engine)
        
        # 資料預處理：去空格與型態轉換
        df["district"] = df["district"].astype(str).str.strip()
        
        def parse_ym(val):
            """內建解析器：處理民國與西元日期混雜問題"""
            try:
                s = str(int(float(val)))
                # 處理民國 11502 -> 2026-02
                if len(s) == 5: return f"{int(s[:3])+1911}-{s[3:]:>02}"
                # 處理西元 202602 -> 2026-02
                if len(s) == 6: return f"{s[:4]}-{s[4:]}"
            except: pass
            return None

        df["年月"] = df["transaction_date"].apply(parse_ym)
        df = df[df["年月"].notna()]
        df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
        df = df[df["total_price"] > 0]

        def calc(sub_df):
            """核心算法：計算單一區域的時序漲跌"""
            if sub_df.empty: return []
            # 依年月排序並取平均值
            m = sub_df.groupby("年月")["total_price"].mean().reset_index().sort_values("年月")
            res = []
            for i, r in m.iterrows():
                mom = None
                if i > 0:
                    prev = m.loc[i-1, 'total_price']
                    if prev != 0:
                        mom = round((r['total_price'] - prev) / prev * 100, 2)
                
                res.append({
                    "年月": r["年月"], 
                    "均總價": round(r["total_price"], 1), 
                    "月增率": mom 
                })
            return res

        # 分支邏輯：特定行政區 vs 全台北市
        if district:
            data = calc(df[df["district"] == district.strip()])
            return clean_json({"district": district, "data": data})
        
        # 批量處理 12 行政區
        result = {d: calc(df[df["district"] == d]) for d in DISTRICTS}
        return clean_json({"unit": "萬", "districts": result})

    except Exception as e:
        import traceback
        print("======== API 500 ERROR TRACEBACK ========")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"趨勢分析失敗: {str(e)}")
