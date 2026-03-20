"""
完整訓練腳本：整合現售價 + 實價登錄
執行方式：python train_all.py
產出：models/ 資料夾內的所有模型檔案
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib, json
from pathlib import Path
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ════════════════════════════════════════════════
# 設定
# ════════════════════════════════════════════════
LISTING_PATH = "/home/frances/tpe-real-estate-ai/final/house_prediction_data.csv"   # 現售價
REAL_PATH    = "/home/frances/tpe-real-estate-ai/final/house_prices_taipei.csv"     # 實價登錄
OUTPUT_DIR   = Path("models")
OUTPUT_DIR.mkdir(exist_ok=True)

# ════════════════════════════════════════════════
# 1. 載入資料
# ════════════════════════════════════════════════
print("[ 1/5 ] 載入資料...")
listing = pd.read_csv(LISTING_PATH)
real    = pd.read_csv(REAL_PATH)
print(f"  現售價：{len(listing):,} 筆")
print(f"  實價登錄：{len(real):,} 筆")

# ════════════════════════════════════════════════
# 2. 現售價整理
# ════════════════════════════════════════════════
print("\n[ 2/5 ] 整理現售價...")

listing["unit_price"]    = listing["total_price"] / listing["building_area"]
listing["floor_ratio"]   = listing["start_floor"] / listing["total_floors"].replace(0, 1)
listing["is_real_price"] = 0
listing["has_parking"]   = listing["parking_space"].clip(0, 1)
listing["house_age"]     = listing["house_age"].fillna(listing["house_age"].median())
listing["type_studio"]   = listing["type_studio"] if "type_studio" in listing.columns else 0
listing["transaction_month"] = 0    # 現售價無交易月份

# ════════════════════════════════════════════════
# 3. 實價登錄整理
# ════════════════════════════════════════════════
print("[ 3/5 ] 整理實價登錄...")

# 民國年月轉為連續數字（例如 11403 → 114*12+3 = 1371）
real["transaction_month"] = (real["transaction_date"] // 100) * 12 + (real["transaction_date"] % 100)
real["is_real_price"]     = 1
real["type_studio"]       = 0   # 實價登錄無此欄位

# 用現售價的區域平均屋齡填補實價登錄缺少的屋齡
district_age = listing.groupby("district")["house_age"].median()
real["house_age"] = real["district"].map(district_age).fillna(listing["house_age"].median())

# 實價登錄無樓層資訊，填入 0.5（中間樓層）
real["floor_ratio"] = 0.5

# ════════════════════════════════════════════════
# 4. 合併與清理
# ════════════════════════════════════════════════
print("[ 4/5 ] 合併資料...")

COMMON_COLS = [
    "unit_price", "building_area", "floor_ratio", "house_age",
    "district", "rooms", "halls", "bathrooms",
    "has_parking", "is_real_price", "transaction_month",
    "type_apartment", "type_building", "type_mansion", "type_house", "type_studio",
    "dist_zhongshan", "dist_zhongzheng", "dist_xinyi",  "dist_neihu",
    "dist_beitou",    "dist_nangang",    "dist_shilin", "dist_datong",
    "dist_daan",      "dist_wenshan",    "dist_songshan","dist_wanhua",
]

df = pd.concat([listing[COMMON_COLS], real[COMMON_COLS]], ignore_index=True)

# 行政區 encoding（合併後統一做，確保編碼一致）
df["district_enc"] = df["district"].astype("category").cat.codes

# 異常值清理：去掉最低 5% 和最高 5%
Q1, Q3 = df["unit_price"].quantile([0.05, 0.95])
df = df[(df["unit_price"] >= Q1) & (df["unit_price"] <= Q3)].copy()
df["log_price"] = np.log1p(df["unit_price"])

print(f"  清理後現售價：{(df['is_real_price']==0).sum():,} 筆")
print(f"  清理後實價登錄：{(df['is_real_price']==1).sum():,} 筆")
print(f"  單價範圍：{df['unit_price'].min():.1f} ~ {df['unit_price'].max():.1f} 萬/坪")

# ════════════════════════════════════════════════
# 5. 訓練預測模型
# ════════════════════════════════════════════════
print("\n[ 5/5 ] 訓練預測模型...")

FEATURES = [
    "building_area", "floor_ratio", "house_age", "district_enc",
    "rooms", "halls", "bathrooms", "has_parking",
    "is_real_price", "transaction_month",
    "type_apartment", "type_building", "type_mansion", "type_house", "type_studio",
    "dist_zhongshan", "dist_zhongzheng", "dist_xinyi",  "dist_neihu",
    "dist_beitou",    "dist_nangang",    "dist_shilin", "dist_datong",
    "dist_daan",      "dist_wenshan",    "dist_songshan","dist_wanhua",
]

# 驗證策略：
# - 用實價登錄做 KFold 驗證（ground truth）
# - 每個 fold 訓練時加入全部現售價（增加樣本量）
# - 只在實價登錄的驗證集上計算 MAPE（避免現售價污染指標）
real_df    = df[df["is_real_price"] == 1].reset_index(drop=True)
listing_df = df[df["is_real_price"] == 0].reset_index(drop=True)

X_real    = real_df[FEATURES].values
y_real    = real_df["log_price"].values
X_listing = listing_df[FEATURES].values
y_listing = listing_df["log_price"].values

kf = KFold(n_splits=5, shuffle=True, random_state=42)
best_iters, mapes = [], []

for fold, (tr, val) in enumerate(kf.split(X_real)):
    # 訓練集 = 實價登錄訓練部分 + 全部現售價
    X_train = np.vstack([X_real[tr], X_listing])
    y_train = np.concatenate([y_real[tr], y_listing])

    m = lgb.LGBMRegressor(
        objective="quantile", alpha=0.5,
        n_estimators=500, learning_rate=0.05,
        num_leaves=31, min_child_samples=20,
        subsample=0.8, colsample_bytree=0.8,
        verbose=-1
    )
    m.fit(
        X_train, y_train,
        eval_set=[(X_real[val], y_real[val])],
        callbacks=[lgb.early_stopping(50, verbose=False)]
    )

    pred   = np.expm1(m.predict(X_real[val]))
    actual = np.expm1(y_real[val])
    mape   = mean_absolute_percentage_error(actual, pred)
    mapes.append(mape)
    best_iters.append(m.best_iteration_)
    print(f"  Fold {fold+1} | best_iter={m.best_iteration_:>4} | MAPE={mape:.2%}")

best_n = int(np.median(best_iters))
print(f"\n  平均 MAPE     : {np.mean(mapes):.2%}")
print(f"  最終 n_estimators : {best_n}")

# 全量資料訓練三個分位數模型
X_all = df[FEATURES].values
y_all = df["log_price"].values

for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
    model = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha,
        n_estimators=best_n, learning_rate=0.05,
        num_leaves=31, min_child_samples=20,
        subsample=0.8, colsample_bytree=0.8,
        verbose=-1
    )
    model.fit(X_all, y_all)
    joblib.dump(model, OUTPUT_DIR / f"lgbm_{name}.pkl")
    print(f"  儲存 lgbm_{name}.pkl")

# 儲存 district encoding 對照表
district_map = dict(enumerate(df["district"].astype("category").cat.categories))
with open(OUTPUT_DIR / "district_map.json", "w") as f:
    json.dump(district_map, f, ensure_ascii=False)

# 儲存特徵順序（API 推論時必須一致）
with open(OUTPUT_DIR / "features.json", "w") as f:
    json.dump(FEATURES, f, ensure_ascii=False)

print("\n  預測模型訓練完成 ✓")

# ════════════════════════════════════════════════
# 6. 訓練分群模型（用實價登錄，成交價較可信）
# ════════════════════════════════════════════════
print("\n[ 分群模型 ] 訓練中...")

district_feat = (
    real_df.groupby("district")
    .agg(
        avg_price   = ("unit_price",    "median"),
        price_std   = ("unit_price",    "std"),
        total_count = ("unit_price",    "count"),
        avg_area    = ("building_area", "mean"),
        avg_rooms   = ("rooms",         "mean"),
    )
    .reset_index()
    .dropna()
)

CLUSTER_FEATURES = ["avg_price", "price_std", "total_count", "avg_area", "avg_rooms"]
Xc = district_feat[CLUSTER_FEATURES].values

scaler    = StandardScaler()
Xc_scaled = scaler.fit_transform(Xc)

kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
district_feat["cluster"] = kmeans.fit_predict(Xc_scaled)

# 依均價自動命名
price_order = district_feat.groupby("cluster")["avg_price"].mean().rank().astype(int)
label_dict  = {1: "平價區", 2: "中低價區", 3: "中價區", 4: "中高價區", 5: "精華高價區"}
district_feat["cluster_label"] = district_feat["cluster"].map(
    lambda c: label_dict[price_order[c]]
)

print("\n  分群結果：")
print(district_feat[["district", "cluster_label", "avg_price", "total_count"]].to_string(index=False))

joblib.dump(kmeans, OUTPUT_DIR / "kmeans.pkl")
joblib.dump(scaler, OUTPUT_DIR / "scaler.pkl")
district_feat.to_csv(OUTPUT_DIR / "district_clusters.csv", index=False)

print("\n  分群模型訓練完成 ✓")
print(f"\n所有模型已儲存至 {OUTPUT_DIR}/")
print("  lgbm_p10.pkl / lgbm_p50.pkl / lgbm_p90.pkl")
print("  kmeans.pkl / scaler.pkl")
print("  district_map.json / features.json / district_clusters.csv")