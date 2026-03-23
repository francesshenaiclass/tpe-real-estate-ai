import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import json
import re
from pathlib import Path
from scipy.spatial import cKDTree

# ════════════════════════════════════════════════
# 1. 絕對路徑設定
# ════════════════════════════════════════════════
ROOT_DIR = Path("/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai")
MRT_CSV = ROOT_DIR / "final" / "清洗後_臺北捷運車站出入口座標.csv"
LISTING_PATH = ROOT_DIR / "final" / "house_prediction_data.csv"
REAL_PATH = ROOT_DIR / "final" / "maxfinal_taipei_real_price_.csv"

OUTPUT_DIR = ROOT_DIR / "models_v3_mrt_cluster"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════
# 2. 載入並處理捷運座標 (CSV 版)
# ════════════════════════════════════════════════
print("(・∀・) 正在讀取捷運 CSV 並建立空間索引...")
mrt_df = pd.read_csv(MRT_CSV)

# 清洗站名：例如 "台北市中山站出口5" -> "中山站"
def clean_station_name(name):
    name = str(name)
    # 移除城市名開頭
    name = re.sub(r"^(台北市|新北市)", "", name)
    # 取到 "站" 為止
    if "站" in name:
        name = name.split("站")[0] + "站"
    return name

mrt_df["station_name"] = mrt_df["出入口名稱"].apply(clean_station_name)
# 同一站的多個出口取座標平均值，簡化成「站點中心」
mrt_centers = mrt_df.groupby("station_name")[["緯度", "經度"]].mean().reset_index()

mrt_coords = mrt_centers[["緯度", "經度"]].values # 緯度=Lat, 經度=Lon
mrt_names = mrt_centers["station_name"].tolist()
mrt_tree = cKDTree(mrt_coords)

# ════════════════════════════════════════════════
# 3. 核心處理函數：座標清洗、時間對齊、商圈標記
# ════════════════════════════════════════════════
def process_data(df, is_listing=False):
    # A. 座標清洗 (解決 ValueError: 'x' must be finite)
    df["latitude"] = pd.to_numeric(df["latitude"], errors='coerce')
    df["longitude"] = pd.to_numeric(df["longitude"], errors='coerce')
    df = df.dropna(subset=["latitude", "longitude"]).copy()
    df = df[np.isfinite(df["latitude"]) & np.isfinite(df["longitude"])].copy()

    # B. 捷運商圈與距離
    dist, idx = mrt_tree.query(df[["latitude", "longitude"]].values)
    df["mrt_cluster_name"] = [mrt_names[i] for i in idx]
    df["distance_to_mrt"] = (dist * 111320).astype(int)

    # C. 時間對齊 (統一為民國總月份)
    if is_listing:
        # 西元 2026-03 -> (2026-1911)*12 + 3 = 1383
        df["temp_time"] = df["updated_at"].fillna(df["created_at"])
        dates = pd.to_datetime(df["temp_time"], errors="coerce")
        df["transaction_month"] = ((dates.dt.year - 1911) * 12) + dates.dt.month
        # 補強：若解析失敗，預設為最新月份 (此處先填0，稍後補齊)
        df["transaction_month"] = df["transaction_month"].fillna(0)
    else:
        # 民國 11502 -> 115*12 + 2 = 1382
        df["transaction_date"] = pd.to_numeric(df["transaction_date"], errors='coerce').fillna(0).astype(int)
        df["transaction_month"] = (df["transaction_date"] // 100) * 12 + (df["transaction_date"] % 100)
    
    # D. 車位判定 (1=有, 0=無)
    if is_listing:
        df["has_parking"] = df["parking_space"].apply(lambda x: 1 if x > 0 else 0)
    else:
        df["has_parking"] = df["has_parking"].fillna(0).astype(int)

    # E. 樓層比
    df["floor_ratio"] = (df["start_floor"] / df["total_floors"].replace(0, 1)).clip(0, 1).fillna(0.5)
    
    return df

print("(・∀ : ) 執行資料清洗與時空轉換...")
real = process_data(pd.read_csv(REAL_PATH), is_listing=False)
listing = process_data(pd.read_csv(LISTING_PATH), is_listing=True)

# 補齊開價資料中缺失的月份 (用實價登錄最新月)
latest_month = real["transaction_month"].max()
listing["transaction_month"] = listing["transaction_month"].replace(0, latest_month).astype(int)

# ════════════════════════════════════════════════
# 4. 編碼與特徵定義
# ════════════════════════════════════════════════
all_mrts = sorted(list(set(listing["mrt_cluster_name"]) | set(real["mrt_cluster_name"])))
mrt_map = {name: i for i, name in enumerate(all_mrts)}
real["mrt_cluster_enc"] = real["mrt_cluster_name"].map(mrt_map)
listing["mrt_cluster_enc"] = listing["mrt_cluster_name"].map(mrt_map)

all_districts = sorted(list(set(real["district"]) | set(listing["district"])))
dist_map = {name: i for i, name in enumerate(all_districts)}
real["district_enc"] = real["district"].map(dist_map)
listing["district_enc"] = listing["district"].map(dist_map)

FEATURES = [
    "building_area", "house_age", "district_enc", "mrt_cluster_enc", 
    "rooms", "halls", "bathrooms", "has_parking", "transaction_month",
    "latitude", "longitude", "distance_to_mrt", "floor_ratio",
    "type_apartment", "type_building", "type_mansion", "type_house"
]

# ════════════════════════════════════════════════
# 5. 模型訓練
# ════════════════════════════════════════════════
def train_and_save(df, is_listing=False):
    df = df.dropna(subset=FEATURES + ["total_price"])
    df = df[df["building_area"] > 0].copy()
    df["unit_price"] = df["total_price"] / df["building_area"]
    
    # 剔除 1% 離群值
    low, high = df["unit_price"].quantile([0.01, 0.99])
    df = df[(df["unit_price"] >= low) & (df["unit_price"] <= high)].copy()
    
    y = np.log1p(df["unit_price"])
    X = df[FEATURES]
    cat_feats = ["district_enc", "mrt_cluster_enc"]
    
    if is_listing:
        print("正在訓練開價模型 (P50)...")
        model = lgb.LGBMRegressor(objective="quantile", alpha=0.5, n_estimators=1000, verbose=-1, random_state=42)
        model.fit(X, y, categorical_feature=cat_feats)
        joblib.dump(model, OUTPUT_DIR / "lgbm_listing_p50.pkl")
    else:
        for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
            print(f"正在訓練實價登錄模型 ({name})...")
            model = lgb.LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=1000, verbose=-1, random_state=42)
            model.fit(X, y, categorical_feature=cat_feats)
            joblib.dump(model, OUTPUT_DIR / f"lgbm_real_{name}.pkl")

train_and_save(real, is_listing=False)
train_and_save(listing, is_listing=True)

# 儲存字典
with open(OUTPUT_DIR / "mrt_cluster_map.json", "w", encoding="utf-8") as f:
    json.dump(mrt_map, f, ensure_ascii=False)
with open(OUTPUT_DIR / "district_map.json", "w", encoding="utf-8") as f:
    json.dump(dist_map, f, ensure_ascii=False)

print(f"(｀皿´) 訓練完成！路徑：{OUTPUT_DIR}")