import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import json
import re
from pathlib import Path
from scipy.spatial import cKDTree
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.preprocessing import LabelEncoder

# ════════════════════════════════════════════════
# 1. 檔案路徑設定
# ════════════════════════════════════════════════
ROOT_DIR = Path("/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai")
MRT_CSV = ROOT_DIR / "final" / "/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/final/清洗後_臺北捷運車站出入口座標.csv"
LISTING_PATH = ROOT_DIR / "final" / "/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/final/house_prediction_data.csv"
REAL_PATH = ROOT_DIR / "final" / "/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/final/house_prices_taipei2.csv"

OUTPUT_DIR = ROOT_DIR / "models_v3_mrt_cluster"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════
# 2. 捷運站點中心化 (KMeans Centroids 概念)
# ════════════════════════════════════════════════
mrt_df = pd.read_csv(MRT_CSV)

def clean_station_name(name):
    name = str(name)
    name = re.sub(r"^(台北市|新北市)", "", name)
    if "站" in name:
        name = name.split("站")[0] + "站"
    return name

mrt_df["station_name"] = mrt_df["出入口名稱"].apply(clean_station_name)
# 計算每個捷運站的中心座標 (Centroids)
mrt_centers = mrt_df.groupby("station_name")[["緯度", "經度"]].mean().reset_index()
mrt_coords = mrt_centers[["緯度", "經度"]].values
mrt_names = mrt_centers["station_name"].tolist()
mrt_tree = cKDTree(mrt_coords)

# 定義絕對地理錨點 (防止邊界溢出，取約略台灣西南角)
ANCHOR_LAT = 24.0
ANCHOR_LON = 120.0

# ════════════════════════════════════════════════
# 3. 資料清理與特徵工程
# ════════════════════════════════════════════════
def process_data(df, is_listing=True):
    df = df.copy()
    
    # 座標基礎清理
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    df = df[np.isfinite(df['latitude']) & np.isfinite(df['longitude'])].copy()
    
    # 【新增特徵】: 中心化座標交互項 (捕捉斜向地段價值)
    df['coord_interact'] = (df['latitude'] - ANCHOR_LAT) * (df['longitude'] - ANCHOR_LON)
    
    # 將房屋分群至最近的捷運站 (Cluster Assignment)
    dist, idx = mrt_tree.query(df[['latitude', 'longitude']].values)
    df['mrt_cluster_name'] = [mrt_names[i] for i in idx]
    
    # 捷運距離處理 (保留使用者計算的距離，若無則用 cKDTree 計算的公尺數)

    df['distance_to_mrt'] = pd.to_numeric(df['distance_to_mrt'], 
    errors='coerce').fillna(pd.Series(dist * 111320, index=df.index))
    
        
    # 時間與常規特徵處理
    if is_listing:
        df["temp_time"] = df["updated_at"].fillna(df["created_at"])
        dates = pd.to_datetime(df["temp_time"], errors="coerce")
        df["transaction_month"] = ((dates.dt.year - 1911) * 12) + dates.dt.month
        df["has_parking"] = (pd.to_numeric(df["parking_space"], errors='coerce').fillna(0) > 0).astype(int)
        df["floor_ratio"] = (pd.to_numeric(df["start_floor"], errors='coerce') / pd.to_numeric(df["total_floors"], errors='coerce').replace(0, 1)).clip(0, 1).fillna(0.5)
    else:
        df["transaction_date"] = pd.to_numeric(df["transaction_date"], errors='coerce').fillna(0).astype(int)
        df["transaction_month"] = (df["transaction_date"] // 100) * 12 + (df["transaction_date"] % 100)
        df["has_parking"] = pd.to_numeric(df["has_parking"], errors='coerce').fillna(0).astype(int)
        df["floor_ratio"] = (pd.to_numeric(df["floor"], errors='coerce') / pd.to_numeric(df["total_floor"], errors='coerce').replace(0, 1)).clip(0, 1).fillna(0.5)
        
    return df

print("(・∀・) 正在讀取並清理資料...")
real_df = process_data(pd.read_csv(REAL_PATH), is_listing=False)
listing_df = process_data(pd.read_csv(LISTING_PATH), is_listing=True)

# 補齊開價資料中缺失的月份 (用實價登錄最新月)
max_month = int(real_df['transaction_month'].max())
listing_df['transaction_month'] = listing_df['transaction_month'].fillna(max_month)

# ════════════════════════════════════════════════
# 4. 類別編碼
# ════════════════════════════════════════════════
all_districts = sorted(list(set(real_df['district']) | set(listing_df['district'])))
all_mrts = sorted(list(set(real_df['mrt_cluster_name']) | set(listing_df['mrt_cluster_name'])))

dist_le = LabelEncoder().fit(all_districts)
mrt_le = LabelEncoder().fit(all_mrts)

for df in [real_df, listing_df]:
    df['district_enc'] = dist_le.transform(df['district'])
    df['mrt_cluster_enc'] = mrt_le.transform(df['mrt_cluster_name'])

# 加入了 coord_interact
FEATURES = [
    "building_area", "house_age", "district_enc", "mrt_cluster_enc", 
    "rooms", "halls", "bathrooms", "has_parking", "transaction_month",
    "latitude", "longitude", "coord_interact", "distance_to_mrt", "floor_ratio",
    "type_apartment", "type_building", "type_mansion", "type_house","type_studio"
]

# ════════════════════════════════════════════════
# 5. 模型訓練與評估 (高中低水位 + 權重)
# ════════════════════════════════════════════════
def train_and_evaluate(df, label_prefix):
    df = df.dropna(subset=FEATURES + ["total_price"])
    df = df[df["building_area"] > 0].copy()
    df["unit_price"] = df["total_price"] / df["building_area"]
    
    # 剔除 1% 極端離群值
    low_b, high_b = df["unit_price"].quantile([0.01, 0.99])
    df = df[(df["unit_price"] >= low_b) & (df["unit_price"] <= high_b)].copy()
    
    y = np.log1p(df["unit_price"])
    X = df[FEATURES]
    cat_feats = ["district_enc", "mrt_cluster_enc"]
    
    stats = {}
    print(f"\n--- 開始訓練 {label_prefix} 模型 ---")
    
    # 訓練 P10(低), P50(中), P90(高)
    for alpha, q_name in [(0.1, "low"), (0.5, "mid"), (0.9, "high")]:
        model = lgb.LGBMRegressor(
            objective='quantile', 
            alpha=alpha, 
            n_estimators=1000, 
            learning_rate=0.05, 
            random_state=42, 
            verbose=-1
        )
        model.fit(X, y, categorical_feature=cat_feats)
        
        # 儲存模型
        model_path = OUTPUT_DIR / f"lgbm_{label_prefix}_{q_name}.pkl"
        joblib.dump(model, model_path)
        
        # 針對中位數 (P50) 計算精準度與權重
        if q_name == "mid":
            preds = np.expm1(model.predict(X))
            mape = mean_absolute_percentage_error(df["unit_price"], preds)
            stats['mape'] = mape
            
            importances = pd.DataFrame({
                'feature': FEATURES,
                'importance': model.feature_importances_
            }).sort_values(by='importance', ascending=False)
            stats['weights'] = importances
            
    return stats

real_stats = train_and_evaluate(real_df, "real")
listing_stats = train_and_evaluate(listing_df, "listing")

# ════════════════════════════════════════════════
# 6. 輸出結果與儲存 Map
# ════════════════════════════════════════════════
print("\n" + "="*50)
print(" 模型評估與權重摘要 ")
print("="*50)
print(f"[實價登錄 P50 模型] 預測誤差 (MAPE): {real_stats['mape']:.2%}")
print(f"[房屋現售 P50 模型] 預測誤差 (MAPE): {listing_stats['mape']:.2%}")

print("\n[實價登錄] 前六大特徵權重:")
print(real_stats['weights'].head(6).to_string(index=False))

print("\n[房屋現售] 前六大特徵權重:")
print(listing_stats['weights'].head(6).to_string(index=False))

# 儲存字典給 API 使用
with open(OUTPUT_DIR / "mrt_cluster_map.json", "w", encoding="utf-8") as f:
    json.dump({k: int(v) for k, v in zip(mrt_le.classes_, mrt_le.transform(mrt_le.classes_))}, f, ensure_ascii=False)
with open(OUTPUT_DIR / "district_map.json", "w", encoding="utf-8") as f:
    json.dump({k: int(v) for k, v in zip(dist_le.classes_, dist_le.transform(dist_le.classes_))}, f, ensure_ascii=False)

print(f"\n(｀皿´) 訓練完成！模型儲存於：{OUTPUT_DIR}")