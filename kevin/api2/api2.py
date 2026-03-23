import pandas as pd
import numpy as np
import joblib
import json
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

# 讓首頁直接回傳 index.html 檔案內容
@app.get("/")
def read_index():
    return FileResponse('index.html')

# 允許跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ════════════════════════════════════════════════
# 1. 載入模型與設定
# ════════════════════════════════════════════════
MODEL_DIR = "../../train/models_v2_final"
models = {
    "listing_p50": joblib.load(f"{MODEL_DIR}/lgbm_listing_p50.pkl"),
    "real_p50": joblib.load(f"{MODEL_DIR}/lgbm_real_p50.pkl"),
    "real_p10": joblib.load(f"{MODEL_DIR}/lgbm_real_p10.pkl"),
    "real_p90": joblib.load(f"{MODEL_DIR}/lgbm_real_p90.pkl")
}

with open(f"{MODEL_DIR}/features.json", "r") as f:
    FEATURES = json.load(f)
with open(f"{MODEL_DIR}/district_map.json", "r") as f:
    DISTRICT_MAP = json.load(f)
    DISTRICT_TO_ENC = {v: int(k) for k, v in DISTRICT_MAP.items()}

# 行政區中英欄位對照表 (用於 One-hot 編碼)
DIST_MAPPING = {
    "中正區": "dist_zhongzheng", "萬華區": "dist_wanhua", "大同區": "dist_datong",
    "中山區": "dist_zhongshan", "松山區": "dist_songshan", "大安區": "dist_daan",
    "信義區": "dist_xinyi", "內湖區": "dist_neihu", "南港區": "dist_nangang",
    "士林區": "dist_shilin", "北投區": "dist_beitou", "文山區": "dist_wenshan"
}

# 各區預設座標 (補足空間特徵)
DISTRICT_COORDS = {
    "中正區": (25.0323, 121.5186), "萬華區": (25.0331, 121.4994), "大同區": (25.0630, 121.5133),
    "中山區": (25.0685, 121.5282), "松山區": (25.0597, 121.5583), "大安區": (25.0263, 121.5283),
    "信義區": (25.0324, 121.5668), "內湖區": (25.0688, 121.5898), "南港區": (25.0548, 121.6068),
    "士林區": (25.0922, 121.5255), "北投區": (25.1321, 121.4987), "文山區": (24.9897, 121.5768)
}

class SearchQuery(BaseModel):
    budget: float
    district: str
    area: float
    house_age: float
    floor: int
    total_floors: int
    mrt_dist: float

def get_realistic_combinations(area):
    """根據坪數產生合理的建議格局組合"""
    combos = []
    if area < 15:
        combos.append((0, 1, 0, 0, 1, 1, 1, 1, "精巧套房 (大樓)"))
        combos.append((1, 0, 0, 0, 1, 1, 1, 1, "傳統套房 (公寓)"))
    elif 15 <= area < 30:
        combos.append((0, 1, 0, 0, 0, 2, 1, 1, "電梯大樓 (2房)"))
        combos.append((1, 0, 0, 0, 0, 2, 2, 1, "實惠公寓 (2房)"))
        combos.append((0, 0, 1, 0, 0, 2, 1, 1, "溫馨華廈 (2房)"))
    else:
        combos.append((0, 1, 0, 0, 0, 3, 2, 2, "家庭大樓 (3房)"))
        combos.append((1, 0, 0, 0, 0, 3, 2, 2, "寬廣公寓 (3房)"))
        combos.append((0, 0, 0, 1, 0, 4, 2, 3, "透天別墅 (4房)"))
    return combos

@app.post("/predict_options")
def predict_options(q: SearchQuery):
    results = []
    # 1. 基礎特徵補全
    floor_ratio = q.floor / q.total_floors if q.total_floors > 0 else 0.5
    lat, lng = DISTRICT_COORDS.get(q.district, (25.03, 121.53))
    
    base_feat = {f: 0 for f in FEATURES}
    base_feat["building_area"] = q.area
    base_feat["floor_ratio"] = floor_ratio
    base_feat["house_age"] = q.house_age
    base_feat["district_enc"] = DISTRICT_TO_ENC.get(q.district, 0)
    base_feat["distance_to_mrt"] = q.mrt_dist
    base_feat["latitude"] = lat
    base_feat["longitude"] = lng
    
    # 修正：設定當前月份代碼 (假設 144 為 2026 年近期)
    base_feat["transaction_month"] = 144 
    
    # 修正：動態觸發 One-hot 行政區特徵 (非常重要)
    target_dist_col = DIST_MAPPING.get(q.district)
    if target_dist_col in base_feat:
        base_feat[target_dist_col] = 1

    # 2. 遍歷格局組合進行預測
    combos = get_realistic_combinations(q.area)
    
    for combo in combos:
        feat = base_feat.copy()
        (feat["type_apartment"], feat["type_building"], feat["type_mansion"], 
         feat["type_house"], feat["type_studio"], feat["rooms"], 
         feat["halls"], feat["bathrooms"], layout_name) = combo
        
        # 準備模型輸入
        input_array = np.array([[feat.get(col, 0) for col in FEATURES]])
        
        # 預測並還原總價 (萬元)
        # 邏輯：exp(log_price) - 1 得到單價，再乘上坪數
        p_list_p50 = np.expm1(models["listing_p50"].predict(input_array)[0]) * q.area
        p_real_p50 = np.expm1(models["real_p50"].predict(input_array)[0]) * q.area
        p_real_p10 = np.expm1(models["real_p10"].predict(input_array)[0]) * q.area
        p_real_p90 = np.expm1(models["real_p90"].predict(input_array)[0]) * q.area
        
        # 判斷是否符合預算 (以成交中位數 P50 為準)
        if p_real_p50 <= q.budget:
            results.append({
                "layout_type": layout_name,
                "listing_p50": int(p_list_p50),
                "real_p50": int(p_real_p50),
                "real_p10": int(p_real_p10),
                "real_p90": int(p_real_p90)
            })
            
    # 依照價格排序，讓最符合預算的排在前面
    results = sorted(results, key=lambda x: x['real_p50'], reverse=True)
    return {"results": results}