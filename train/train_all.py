import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib, json
import os
from pathlib import Path
from sklearn.cluster import KMeans

# ════════════════════════════════════════════════
# 1. 自動路徑與資料夾設定 (解決路徑報錯)
# ════════════════════════════════════════════════
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
# 模型儲存位置
OUTPUT_DIR = CURRENT_DIR / "models_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # 修正：加上 parents=True

# 資料讀取位置 (請確認檔案放在專案根目錄下的 final/ 資料夾)
LISTING_PATH = BASE_DIR / "final" / "house_prediction_data.csv"
REAL_PATH    = BASE_DIR / "final" / "house_prices_taipei.csv"

# ════════════════════════════════════════════════
# 2. 載入原始資料
# ════════════════════════════════════════════════
print("[ 1/5 ] 載入資料並進行基礎清洗...")
listing = pd.read_csv(LISTING_PATH)
real    = pd.read_csv(REAL_PATH)

# 防呆：移除經緯度為空的無效資料
for df in [listing, real]:
    df.dropna(subset=["latitude", "longitude", "distance_to_mrt"], inplace=True)
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)

# ════════════════════════════════════════════════
# 3. 特徵生成與對齊 (核心修正：先算單價，再做過濾)
# ════════════════════════════════════════════════
print("\n[ 2/5 ] 特徵生成與空間聚類 (方案 A)...")

# A. 計算單價 (萬/坪)
listing["unit_price"] = listing["total_price"] / listing["building_area"]
# 實價登錄檔案中已經有 unit_price 了，如果不確定，再算一次確保單位一致

# B. 執行 K-Means 空間聚類 (商圈定義)
print("   >> 正在定義 500 個商圈中心...")
coords_train = real[["latitude", "longitude"]].values
spatial_kmeans = KMeans(n_clusters=500, random_state=42, n_init=10)
real["area_cluster"] = spatial_kmeans.fit_predict(coords_train)
# 開價資料套用同樣的分群邏輯
listing["area_cluster"] = spatial_kmeans.predict(listing[["latitude", "longitude"]].values)
# 存檔供 API 使用
joblib.dump(spatial_kmeans, OUTPUT_DIR / "spatial_kmeans.pkl")

# C. 處理其他衍生特徵
listing["floor_ratio"] = listing["start_floor"] / listing["total_floors"].replace(0, 1)
listing["has_parking"] = listing["parking_space"].clip(0, 1) # 把車位數轉為 0/1
listing["transaction_month"] = 0 # 開價資料無交易月份，設為 0

# 實價登錄的月份計算 (例如 11301 -> 月份流水號)
real["transaction_month"] = (real["transaction_date"] // 100) * 12 + (real["transaction_date"] % 100)
real["floor_ratio"] = 0.5 # 實價登錄通常沒樓層詳細資訊，設中間值

# 行政區編碼對齊
all_districts = pd.concat([listing["district"], real["district"]]).astype("category")
dist_cats = all_districts.cat.categories
listing["district_enc"] = pd.Categorical(listing["district"], categories=dist_cats).codes
real["district_enc"]    = pd.Categorical(real["district"], categories=dist_cats).codes

# D. 定義模型需要的特徵清單 (這也是 API 需要的順序)
FEATURES = [
    "building_area", "floor_ratio", "house_age", "district_enc",
    "area_cluster", "rooms", "halls", "bathrooms", "has_parking", "transaction_month",
    "latitude", "longitude", "distance_to_mrt",
    "type_apartment", "type_building", "type_mansion", "type_house", "type_studio",
    "dist_zhongshan", "dist_zhongzheng", "dist_xinyi",  "dist_neihu",
    "dist_beitou",    "dist_nangang",    "dist_shilin", "dist_datong",
    "dist_daan",      "dist_wenshan",    "dist_songshan","dist_wanhua",
]

# 建立用於訓練的 DF
listing_df = listing[["unit_price"] + FEATURES].copy()
real_df    = real[["unit_price"] + FEATURES].copy()

# ════════════════════════════════════════════════
# 4. 離群值清洗 (這下不會 KeyError 了)
# ════════════════════════════════════════════════
print("\n[ 3/5 ] 執行離群值清洗與對數轉換...")

def clean_outliers(df):
    # 排除極端 1% 的價格 (如豪宅或破房)
    low, high = df["unit_price"].quantile([0.01, 0.99])
    df = df[(df["unit_price"] >= low) & (df["unit_price"] <= high)].copy()
    # 價格對數化 (讓模型更好學)
    df["log_price"] = np.log1p(df["unit_price"])
    return df

listing_df = clean_outliers(listing_df)
real_df    = clean_outliers(real_df)

# ════════════════════════════════════════════════
# 5. 模型訓練 (實價 p10, p50, p90 + 開價 p50)
# ════════════════════════════════════════════════
print("\n[ 4/5 ] 訓練模型 (Quantile Regression)...")

X_real = real_df[FEATURES]
y_real = real_df["log_price"]

cat_feats = ["district_enc", "area_cluster"] # 明確告知哪些是標籤

for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
    model = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha, n_estimators=500, learning_rate=0.05,
        num_leaves=31, min_child_samples=50, verbose=-1
    )
    model.fit(X_real, y_real, categorical_feature=cat_feats)
    joblib.dump(model, OUTPUT_DIR / f"lgbm_real_{name}.pkl")
    print(f"    ✅ 已儲存 lgbm_real_{name}.pkl")

# 訓練市場開價模型 (p50)
X_listing = listing_df[FEATURES]
y_listing = listing_df["log_price"]
model_list = lgb.LGBMRegressor(
    objective="quantile", alpha=0.5, n_estimators=500, learning_rate=0.05, verbose=-1
)
model_list.fit(X_listing, y_listing, categorical_feature=cat_feats)
joblib.dump(model_list, OUTPUT_DIR / "lgbm_listing_p50.pkl")
print(f"    ✅ 已儲存 lgbm_listing_p50.pkl")

# 儲存對照表
with open(OUTPUT_DIR / "features.json", "w") as f:
    json.dump(FEATURES, f, ensure_ascii=False)
with open(OUTPUT_DIR / "district_map.json", "w") as f:
    json.dump(dict(enumerate(dist_cats)), f, ensure_ascii=False)

print("\n[ 5/5 ] 模型與空間聚類器已成功更新至 models_v2/ (ˇωˇ)")