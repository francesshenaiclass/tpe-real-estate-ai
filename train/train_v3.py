import joblib
import json
import pandas as pd

# 1. 指定你的模型路徑
MODEL_DIR = "/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/train/models_v2"

# 2. 讀取「 context 」( 之前存好的特徵清單與模型 )
with open(f"{MODEL_DIR}/features.json", "r") as f:
    FEATURES = json.load(f)

model_list = joblib.load(f"{MODEL_DIR}/lgbm_listing_p50.pkl")

# 3. 現在 Python 知道變數是什麼了，可以跑分析了
importance_df = pd.DataFrame({
    'feature': FEATURES,
    'importance_gain': model_list.booster_.feature_importance(importance_type='gain')
}).sort_values(by='importance_gain', ascending=False)

print("★ 分析已存檔模型之特徵重要性：")
print(importance_df.head(10))