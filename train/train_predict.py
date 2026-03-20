import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from sklearn.model_selection import TimeSeriesSplit

df = pd.read_csv("final/house_prediction_data.csv")

=======基本清理=======
df["unit_price"] = df["總價元"] / df["建物移轉總面積坪"] / 10000
Q1, Q3 = df["unit_price"].quantile([0.05, 0.95])
df = df[(df["unit_price"] >= Q1) & (df["unit_price"] <= Q3)]
df["log_price"] = np.log1p(df["unit_price"])
df["樓層比"] = df["樓層"] / df["總樓層數"]
df["district_enc"] = df["鄉鎮市區"].astype("category").cat.codes
df = df.sort_values("交易年月_num")

FEATURES = ["建物移轉總面積坪", "樓層比", "屋齡", "district_enc", "交易年月_num"]
X = df[FEATURES].values
y = df["log_price"].values

# 用最後一個 fold 的 best_iter 決定最終 n_estimators
tscv = TimeSeriesSplit(n_splits=5)
best_iters = []

for fold, (tr, val) in enumerate(tscv.split(X)):
    m = lgb.LGBMRegressor(
        objective="quantile", alpha=0.5,
        n_estimators=500, learning_rate=0.05,
        num_leaves=31, verbose=-1
    )
    m.fit(X[tr], y[tr],
          eval_set=[(X[val], y[val])],
          callbacks=[lgb.early_stopping(50, verbose=False)])
    best_iters.append(m.best_iteration_)

best_n = int(np.median(best_iters))

========訓練三個分位數模型（全量）=======
for alpha, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
    model = lgb.LGBMRegressor(
        objective="quantile", alpha=alpha,
        n_estimators=best_n, learning_rate=0.05,
        num_leaves=31, verbose=-1
    )
    model.fit(X, y)
    joblib.dump(model, f"models/lgbm_{name}.pkl")
    print(f"儲存 lgbm_{name}.pkl")

# 儲存 encoding 對照表（API 推論時需要）
district_map = dict(enumerate(df["鄉鎮市區"].astype("category").cat.categories))
import json
with open("models/district_map.json", "w") as f:
    json.dump(district_map, f, ensure_ascii=False)

print("預測模型訓練完成")