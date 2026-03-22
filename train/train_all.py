import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib, json
import os
from pathlib import Path
from sklearn.cluster import KMeans

# ════════════════════════════════════════════════
# 1. 路徑設定 (手動指定至你的 final 資料夾)
# ════════════════════════════════════════════════
DATA_DIR = Path("/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/final")
OUTPUT_DIR = DATA_DIR.parent / "models_v2_final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LISTING_PATH = DATA_DIR / "house_prediction_data.csv"
REAL_PATH    = DATA_DIR / "maxfinal_taipei_real_price_.csv"

# ════════════════════════════════════════════════
# 2. 載入原始資料與基礎清洗
# ════════════════════════════════════════════════
print(f"[ 1/5 ] 正在載入資料...")
if not LISTING_PATH.exists() or not REAL_PATH.exists():
    print(f"❌ 錯誤：在 {DATA_DIR} 找不到 CSV 檔案。")
    exit()

listing = pd.read_csv(LISTING_PATH)
real    = pd.read_csv(REAL_PATH)

for df in [listing, real]:
    critical_cols = ["latitude", "longitude", "distance_to_mrt", "building_area", "total_price"]
    df.dropna(subset=critical_cols, inplace=True)
    df = df[df["building_area"] > 0].copy()

# ════════════════════════════════════════════════
# 3. 特徵生成與對齊 (k=250)
# ════════════════════════════════════════════════
print("\n[ 2/5 ] 特徵生成與空間聚類 (k=250)...")

# A. 統一計算單價
listing["unit_price"] = listing["total_price"] / listing["building_area"]

# B. 執行 K-Means
coords_train = real[["latitude", "longitude"]].values
spatial_kmeans = KMeans(n_clusters=250, random_state=42, n_init=10)
real["area_cluster"] = spatial_kmeans.fit_predict(coords_train)
listing["area_cluster"] = spatial_kmeans.predict(listing[["latitude", "longitude"]].values)
joblib.dump(spatial_kmeans, OUTPUT_DIR / "spatial_kmeans.pkl")

# C. 處理衍生特徵 (樓層、車位、月份)
listing["floor_ratio"] = (listing["start_floor"] / listing["total_floors"].replace(0, 1)).clip(0, 1).fillna(0.5)
real["floor_ratio"]    = (real["start_floor"]    / real["total_floors"].replace(0, 1)).clip(0, 1).fillna(0.5)

listing["has_parking"] = listing["parking_space"].clip(0, 1)
listing["transaction_month"] = 0 
real["transaction_date"] = real["transaction_date"].fillna(0).astype(int)
real["transaction_month"] = (real["transaction_date"] // 100) * 12 + (real["transaction_date"] % 100)

# 行政區編碼對齊
all_districts = pd.concat([listing["district"], real["district"]]).astype("category")
dist_cats = all_districts.cat.categories
listing["district_enc"] = pd.Categorical(listing["district"], categories=dist_cats).codes
real["district_enc"]    = pd.Categorical(real["district"], categories=dist_cats).codes

# D. 定義模型特徵清單 (已刪除 type_studio)
FEATURES = [
    "building_area", "floor_ratio", "house_age", "district_enc",
    "area_cluster", "rooms", "halls", "bathrooms", "has_parking", "transaction_month",
    "latitude", "longitude", "distance_to_mrt",
    "type_apartment", "type_building", "type_mansion", "type_house"
]
dist_cols = [c for c in real.columns if c.startswith("dist_") and c != "distance_to_mrt"]
FEATURES += dist_cols

# 💡 修正 NameError：在這裡先定義 DataFrame
listing_df = listing[["unit_price"] + FEATURES].copy()
real_df    = real[["unit_price"] + FEATURES].copy()

# ════════════════════════════════════════════════
# 4. 離群值清洗與對數轉換
# ════════════════════════════════════════════════
print("\n[ 3/5 ] 執行離群值清洗與對數轉換...")

def clean_outliers(df):
    low, high = df["unit_price"].quantile([0.01, 0.99])
    df = df[(df["unit_price"] >= low) & (df["unit_price"] <= high)].copy()
    df["log_price"] = np.log1p(df["unit_price"])
    return df

listing_df = clean_outliers(listing_df)
real_df    = clean_outliers(real_df)

# ════════════════════════════════════════════════
# 5. 模型訓練 (p10, p50, p90)
# ════════════════════════════════════════════════
print("\n[ 4/5 ] 正在訓練模型 (p10, p50, p90)...")

X_real = real_df[FEATURES]
y_real = real_df["log_price"]
cat_feats = ["district_enc", "area_cluster"]

for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
    model = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha, n_estimators=500, learning_rate=0.05,
        num_leaves=31, min_child_samples=30, verbose=-1, random_state=42
    )
    model.fit(X_real, y_real, categorical_feature=cat_feats)
    joblib.dump(model, OUTPUT_DIR / f"lgbm_real_{name}.pkl")
    print(f"    ✅ 已儲存 lgbm_real_{name}.pkl")

# 開價模型
model_list = lgb.LGBMRegressor(objective="quantile", alpha=0.5, n_estimators=500, verbose=-1, random_state=42)
model_list.fit(listing_df[FEATURES], listing_df["log_price"], categorical_feature=cat_feats)
joblib.dump(model_list, OUTPUT_DIR / "lgbm_listing_p50.pkl")

with open(OUTPUT_DIR / "features.json", "w", encoding='utf-8') as f:
    json.dump(FEATURES, f, ensure_ascii=False)
with open(OUTPUT_DIR / "district_map.json", "w", encoding='utf-8') as f:
    json.dump(dict(enumerate(dist_cats)), f, ensure_ascii=False)

print(f"\n[ 5/5 ] 模型已成功儲存至 {OUTPUT_DIR} (ˇωˇ)")