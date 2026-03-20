"""
台北市實價登錄 — 各行政區月均總價漲幅 API
================================================
啟動：
    pip install flask flask-cors pandas pymysql
    python api.py

端點：
    GET  /health
         → { status, db_connected, total_rows }

    GET  /api/monthly-growth
         → { unit, districts: { "大安區": [{年月, 均總價, 月增率}, ...], ... } }

    GET  /api/monthly-growth?district=大安區
         → { district, unit, data: [{年月, 均總價, 月增率}, ...] }

    GET  /api/ranking?month=2024-03
         → { month, unit, ranking: [{rank, district, 均總價, 月增率}, ...] }

    GET  /api/months
         → { months: ["2023-01", ...] }
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import pymysql
import math
from dotenv import load_dotenv  # 從 .env 檔載入環境變
import os

app = Flask(__name__)
CORS(app)

# ── 資料庫連線設定 ─────────────────────────────────────────
DB_CONFIG = {
    "host":    "dv108.aiturn.fun",
    "port":    3306,           
    "user":    "betty",
    "password":  os.getenv("DB_PASSWORD"),    # ← 填入你的 MySQL 密碼
    "database": "db_realestate",
    "charset":  "utf8mb4",
}
TABLE = "house_prices_taipei"

DISTRICTS = [
    "中正區","大同區","中山區","松山區","大安區","萬華區",
    "信義區","士林區","北投區","內湖區","南港區","文山區",
]

# ── 資料載入 ──────────────────────────────────────────────
def load_df():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        df = pd.read_sql(
            f"SELECT district, transaction_date, total_price FROM `{TABLE}`",
            conn
        )
        conn.close()
    except Exception as e:
        return None, f"資料庫連線失敗：{e}"

    # district 欄位直接是中文區名，重新命名對齊後續邏輯
    df = df.rename(columns={
        "district":        "行政區",
        "total_price":     "房屋總價",
        "transaction_date":"成交年月_raw",
    })
    df = df[df["行政區"].notna()]

    # 解析成交年月
    # transaction_date 為民國 5 碼整數，例如 11302 → 2024-02
    def parse_ym(val):
        try:
            s = str(int(float(val)))
            if len(s) == 5:
                return f"{int(s[:3])+1911}-{s[3:]:>02}"
            if len(s) == 6:
                return f"{s[:4]}-{s[4:]}"
        except Exception:
            pass
        return None

    df["年月"] = df["成交年月_raw"].apply(parse_ym)
    df = df[df["年月"].notna()]

    # 總價數值化、過濾異常值
    df["房屋總價"] = pd.to_numeric(df["房屋總價"], errors="coerce")
    df = df[df["房屋總價"] > 0]

    return df, None


# ── 計算月增率 ────────────────────────────────────────────
def calc_monthly_growth(df, district=None):
    """
    回傳清單：[{年月, 均總價, 月增率}, ...]
    月增率 = (本月均價 - 上月均價) / 上月均價 × 100，第一筆為 null
    """
    if district:
        df = df[df["行政區"] == district]
    if df.empty:
        return []

    monthly = (
        df.groupby("年月")["房屋總價"]
        .mean()
        .reset_index()
        .rename(columns={"房屋總價": "均總價"})
        .sort_values("年月")
        .reset_index(drop=True)
    )
    monthly["均總價"] = monthly["均總價"].round(1)

    result = []
    for i, row in monthly.iterrows():
        mom = None
        if i > 0:
            prev = monthly.loc[i-1, "均總價"]
            if prev and prev > 0:
                mom = round((row["均總價"] - prev) / prev * 100, 2)
        result.append({
            "年月":   row["年月"],
            "均總價": row["均總價"],
            "月增率": mom,
        })
    return result


def clean(obj):
    """NaN → None，供 jsonify 使用"""
    if isinstance(obj, list):  return [clean(i) for i in obj]
    if isinstance(obj, dict):  return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, float) and math.isnan(obj): return None
    return obj


# ── 路由 ──────────────────────────────────────────────────
@app.route("/health")
def health():
    df, err = load_df()
    if err:
        return jsonify({"status": "error", "message": err}), 500
    return jsonify({
        "status":       "ok",
        "db_connected": True,
        "total_rows":   len(df),
    })


@app.route("/api/months")
def get_months():
    df, err = load_df()
    if err: return jsonify({"error": err}), 500
    months = sorted(df["年月"].unique().tolist())
    return jsonify({"months": months})


@app.route("/api/monthly-growth")
def monthly_growth():
    df, err = load_df()
    if err: return jsonify({"error": err}), 500

    district = request.args.get("district", "").strip()

    # 單區
    if district:
        data = calc_monthly_growth(df, district)
        if not data:
            return jsonify({"error": f"找不到 {district} 的資料"}), 404
        return jsonify(clean({
            "district": district,
            "unit":     "萬",
            "data":     data,
        }))

    # 全區
    result = {}
    for d in DISTRICTS:
        rows = calc_monthly_growth(df, d)
        if rows:
            result[d] = rows

    return jsonify(clean({
        "unit":      "萬",
        "districts": result,
    }))


@app.route("/api/ranking")
def ranking():
    """取得指定月份的各區月增率排行"""
    df, err = load_df()
    if err: return jsonify({"error": err}), 500

    # 預設取最新月份
    all_months = sorted(df["年月"].unique().tolist())
    target_month = request.args.get("month", all_months[-1] if all_months else "")

    rank_list = []
    for d in DISTRICTS:
        data = calc_monthly_growth(df, d)
        row = next((x for x in data if x["年月"] == target_month), None)
        if row and row["月增率"] is not None:
            rank_list.append({
                "district": d,
                "均總價":   row["均總價"],
                "月增率":   row["月增率"],
            })

    rank_list.sort(key=lambda x: x["月增率"], reverse=True)
    for i, item in enumerate(rank_list):
        item["rank"] = i + 1

    return jsonify(clean({
        "month":   target_month,
        "unit":    "萬",
        "ranking": rank_list,
    }))


if __name__ == "__main__":
    print("=" * 50)
    print("🏠  台北市房價月增率 API")
    print(f"🗄️   資料庫：{DB_CONFIG['host']} / {DB_CONFIG['database']} / {TABLE}")
    print("📡  端點：")
    print("    GET  /health")
    print("    GET  /api/months")
    print("    GET  /api/monthly-growth")
    print("    GET  /api/monthly-growth?district=大安區")
    print("    GET  /api/ranking?month=2024-03")
    print("=" * 50)
    app.run(debug=True, port=5000)