# app.py
from fastapi import FastAPI
import joblib, json, numpy as np

app = FastAPI()

# 啟動時載入一次，之後每個請求都重複使用
m_p10 = joblib.load("models/lgbm_p10.pkl")
m_p50 = joblib.load("models/lgbm_p50.pkl")
m_p90 = joblib.load("models/lgbm_p90.pkl")

with open("models/district_map.json") as f:
    district_map = json.load(f)
reverse_map = {v: int(k) for k, v in district_map.items()}

with open("models/features.json") as f:
    FEATURES = json.load(f)


from pydantic import BaseModel

# 定義用戶要傳入的欄位
class PredictRequest(BaseModel):
    district:      str    # 行政區，例如 "大安區"
    building_area: float  # 坪數
    house_age:     float  # 屋齡
    start_floor:   int    # 所在樓層
    total_floors:  int    # 總樓層數
    rooms:         int = 2
    halls:         int = 1
    bathrooms:     int = 1
    has_parking:   int = 0

@app.post("/api/predict")
def predict_price(req: PredictRequest):

    # 1. 把用戶輸入組成模型看得懂的特徵向量
    enc = reverse_map.get(req.district)
    floor_ratio = req.start_floor / max(req.total_floors, 1)

    dist_flags = {col: 0 for col in [
        "dist_zhongshan","dist_zhongzheng","dist_xinyi","dist_neihu",
        "dist_beitou","dist_nangang","dist_shilin","dist_datong",
        "dist_daan","dist_wenshan","dist_songshan","dist_wanhua"
    ]}
    dist_col_map = {
        "中山區":"dist_zhongshan", "中正區":"dist_zhongzheng",
        "信義區":"dist_xinyi",     "內湖區":"dist_neihu",
        "北投區":"dist_beitou",    "南港區":"dist_nangang",
        "士林區":"dist_shilin",    "大同區":"dist_datong",
        "大安區":"dist_daan",      "文山區":"dist_wenshan",
        "松山區":"dist_songshan",  "萬華區":"dist_wanhua",
    }
    if req.district in dist_col_map:
        dist_flags[dist_col_map[req.district]] = 1

    row = {
        "building_area":  req.building_area,
        "floor_ratio":    floor_ratio,
        "house_age":      req.house_age,
        "district_enc":   enc,
        "rooms":          req.rooms,
        "halls":          req.halls,
        "bathrooms":      req.bathrooms,
        "has_parking":    req.has_parking,
        "is_real_price":  0,          # 推論時固定為 0（用戶輸入的是掛牌條件）
        "transaction_month": 0,
        "type_apartment": 0,
        "type_building":  1,          # 預設公寓大樓
        "type_mansion":   0,
        "type_house":     0,
        "type_studio":    0,
        **dist_flags,
    }

    X = np.array([[row[f] for f in FEATURES]])

    # 2. 三個模型各預測一次，還原 log
    p10 = round(float(np.expm1(m_p10.predict(X)[0])), 1)
    p50 = round(float(np.expm1(m_p50.predict(X)[0])), 1)
    p90 = round(float(np.expm1(m_p90.predict(X)[0])), 1)

    # 3. 回傳 JSON
    return {
        "district":        req.district,
        "estimated_price": p50,
        "price_range": {
            "low":  p10,
            "mid":  p50,
            "high": p90,
        },
        "estimated_total": round(p50 * req.building_area, 0),
        "unit": "萬/坪"
    }
