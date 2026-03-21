"""
完整訓練腳本：雙模型架構 + 實價分位數 (p10, p50, p90) + 開價中位數 (p50)
產出：models_v3/
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib, json
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ════════════════════════════════════════════════
# 設定
# ════════════════════════════════════════════════
LISTING_PATH = "/Users/laylatang8537/Documents/vscold/專題作業/tpe-real-estate-ai/final/house_prediction_data.csv"
REAL_PATH    = "/Users/laylatang8537/Documents/vscold/專題作業/tpe-real-estate-ai/final/house_prices_taipei.csv"

# 建立全新的 v2 資料夾確保版本安全
OUTPUT_DIR = Path("/Users/laylatang8537/Documents/vscold/專題作業/tpe-real-estate-ai/train/models_v2")
OUTPUT_DIR.mkdir(exist_ok=True)

# ════════════════════════════════════════════════
# 1. 載入資料與空間特徵防呆
# ════════════════════════════════════════════════
print("[ 1/4 ] 載入資料...")
listing = pd.read_csv(LISTING_PATH)
real    = pd.read_csv(REAL_PATH)

for df in [listing, real]:
    df.dropna(subset=["latitude", "longitude", "distance_to_mrt"], inplace=True)
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)
    df["distance_to_mrt"] = df["distance_to_mrt"].astype(float)

# ════════════════════════════════════════════════
# 2. 特徵對齊與離群值處理
# ════════════════════════════════════════════════
print("\n[ 2/4 ] 特徵對齊與排除離群值...")

COMMON_COLS = [
    "unit_price", "building_area", "floor_ratio", "house_age",
    "district", "rooms", "halls", "bathrooms",
    "has_parking", "transaction_month",
    "type_apartment", "type_building", "type_mansion", "type_house", "type_studio",
    "latitude", "longitude", "distance_to_mrt",
    "dist_zhongshan", "dist_zhongzheng", "dist_xinyi",  "dist_neihu",
    "dist_beitou",    "dist_nangang",    "dist_shilin", "dist_datong",
    "dist_daan",      "dist_wenshan",    "dist_songshan","dist_wanhua",
]

listing["unit_price"]    = listing["total_price"] / listing["building_area"]
listing["floor_ratio"]   = listing["start_floor"] / listing["total_floors"].replace(0, 1)
listing["has_parking"]   = listing["parking_space"].clip(0, 1)
listing["house_age"]     = listing["house_age"].fillna(listing["house_age"].median())
listing["type_studio"]   = listing["type_studio"] if "type_studio" in listing.columns else 0
listing["transaction_month"] = 0 

real["transaction_month"] = (real["transaction_date"] // 100) * 12 + (real["transaction_date"] % 100)
real["type_studio"]       = 0 
real["floor_ratio"]       = 0.5 

district_age = listing.groupby("district")["house_age"].median()
real["house_age"] = real["district"].map(district_age).fillna(listing["house_age"].median())

listing_df = listing[COMMON_COLS].copy()
real_df    = real[COMMON_COLS].copy()

all_districts = pd.concat([listing_df["district"], real_df["district"]]).astype("category")
district_categories = all_districts.cat.categories
listing_df["district_enc"] = pd.Categorical(listing_df["district"], categories=district_categories).codes
real_df["district_enc"]    = pd.Categorical(real_df["district"], categories=district_categories).codes

def clean_outliers(df):
    Q1, Q3 = df["unit_price"].quantile([0.01, 0.99])
    df = df[(df["unit_price"] >= Q1) & (df["unit_price"] <= Q3)].copy()
    df["log_price"] = np.log1p(df["unit_price"])
    return df

listing_df = clean_outliers(listing_df)
real_df    = clean_outliers(real_df)

# ════════════════════════════════════════════════
# 3. 訓練預測模型 (實價 3 個分位數 + 開價 1 個中位數)
# ════════════════════════════════════════════════
print("\n[ 3/4 ] 訓練預測模型...")

FEATURES = [
    "building_area", "floor_ratio", "house_age", "district_enc",
    "rooms", "halls", "bathrooms", "has_parking", "transaction_month",
    "latitude", "longitude", "distance_to_mrt",
    "type_apartment", "type_building", "type_mansion", "type_house", "type_studio",
    "dist_zhongshan", "dist_zhongzheng", "dist_xinyi",  "dist_neihu",
    "dist_beitou",    "dist_nangang",    "dist_shilin", "dist_datong",
    "dist_daan",      "dist_wenshan",    "dist_songshan","dist_wanhua",
]

# 3-1: 訓練實價登錄 (p10, p50, p90)
X_real = real_df[FEATURES].values
y_real = real_df["log_price"].values

print("  >> 訓練實價登錄合理區間模型...")
for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
    # p10 與 p90 需要更高的 min_child_samples 來抗噪聲
    min_child = 80 if alpha != 0.5 else 50
    model = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha,
        n_estimators=500, learning_rate=0.05,
        num_leaves=31, min_child_samples=min_child,
        subsample=0.8, colsample_bytree=0.8, verbose=-1
    )
    model.fit(X_real, y_real)
    joblib.dump(model, OUTPUT_DIR / f"lgbm_real_{name}.pkl")
    print(f"    儲存 lgbm_real_{name}.pkl")

# 3-2: 訓練市場開價 (僅 p50)
X_listing = listing_df[FEATURES].values
y_listing = listing_df["log_price"].values

print("  >> 訓練市場開價預估模型...")
model_list = lgb.LGBMRegressor(
    objective="quantile", alpha=0.5,
    n_estimators=500, learning_rate=0.05,
    num_leaves=31, min_child_samples=50,
    subsample=0.8, colsample_bytree=0.8, verbose=-1
)
model_list.fit(X_listing, y_listing)
joblib.dump(model_list, OUTPUT_DIR / "lgbm_listing_p50.pkl")
print(f"    儲存 lgbm_listing_p50.pkl")

# 儲存對照表
district_map = dict(enumerate(district_categories))
with open(OUTPUT_DIR / "district_map.json", "w") as f:
    json.dump(district_map, f, ensure_ascii=False)

with open(OUTPUT_DIR / "features.json", "w") as f:
    json.dump(FEATURES, f, ensure_ascii=False)

# ════════════════════════════════════════════════
# 4. 訓練分群模型
# ════════════════════════════════════════════════
print("\n[ 4/4 ] 訓練區域分群模型...")

district_feat = (
    real_df.groupby("district")
    .agg(
        avg_price   = ("unit_price",    "median"),
        price_std   = ("unit_price",    "std"),
        total_count = ("unit_price",    "count"),
        avg_area    = ("building_area", "mean"),
        avg_rooms   = ("rooms",         "mean"),
        avg_dist    = ("distance_to_mrt", "median")
    )
    .reset_index()
    .dropna()
)

CLUSTER_FEATURES = ["avg_price", "price_std", "total_count", "avg_area", "avg_rooms", "avg_dist"]
Xc = district_feat[CLUSTER_FEATURES].values

scaler = StandardScaler()
Xc_scaled = scaler.fit_transform(Xc)

kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
district_feat["cluster"] = kmeans.fit_predict(Xc_scaled)

price_order = district_feat.groupby("cluster")["avg_price"].mean().rank().astype(int)
label_dict  = {1: "平價區", 2: "中低價區", 3: "中價區", 4: "中高價區", 5: "精華高價區"}
district_feat["cluster_label"] = district_feat["cluster"].map(lambda c: label_dict[price_order[c]])

joblib.dump(kmeans, OUTPUT_DIR / "kmeans.pkl")
joblib.dump(scaler, OUTPUT_DIR / "scaler.pkl")
district_feat.to_csv(OUTPUT_DIR / "district_clusters.csv", index=False)

print("\n模型已成功儲存至 models_v2/ 資料夾 O_O")