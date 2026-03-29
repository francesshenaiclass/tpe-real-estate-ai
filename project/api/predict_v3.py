from fastapi import APIRouter, HTTPException
import numpy as np
import joblib, json
from pathlib import Path

# 1. 初始化 Router
router = APIRouter(prefix="/api/predict", tags=["AI 精準預估"])

# 2. 設定路徑 (project/api/predict_v3.py -> project/)
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"

# 19 個特徵順序 (嚴格對齊 V3 模型訓練順序)
FEATURES = [
    "building_area", "house_age", "district_enc", "mrt_cluster_enc", 
    "rooms", "halls", "bathrooms", "has_parking", "transaction_month", 
    "latitude", "longitude", "coord_interact", "distance_to_mrt", 
    "floor_ratio", "type_apartment", "type_building", "type_mansion", 
    "type_house", "type_studio"
]

# 資源容器
models = {}
maps = {}

def init():
    global models, maps
    try:
        # A. 載入 6 個模型 (實價登錄 3 個 + 開價 3 個)
        mapping = {
            "real_low": "lgbm_real_low.pkl", 
            "real_mid": "lgbm_real_mid.pkl", 
            "real_high": "lgbm_real_high.pkl",
            "list_low": "lgbm_listing_low.pkl",
            "list_mid": "lgbm_listing_mid.pkl",
            "list_high": "lgbm_listing_high.pkl"
        }
        for key, filename in mapping.items():
            fpath = MODEL_DIR / filename
            if fpath.exists():
                tmp = joblib.load(fpath)
                # 提取 Booster 核心以防止版本不相容
                models[key] = tmp.booster_ if hasattr(tmp, 'booster_') else tmp
        
        # B. 載入編碼映射表
        with open(STATIC_DIR / "district_map.json", "r", encoding="utf-8") as f:
            maps["dist"] = json.load(f)
        with open(STATIC_DIR / "mrt_cluster_map.json", "r", encoding="utf-8") as f:
            maps["mrt"] = json.load(f)
            
        print("✅ Predict V3 模組資源載入成功")
    except Exception as e:
        print(f"❌ Predict V3 模組載入失敗: {e}")

# 執行初始化
init()

# ════════════════════════════════════════════════
# API 端點
# ════════════════════════════════════════════════

@router.post("/v3")
async def do_predict(req: dict):
    """
    接收前端參數，進行特徵工程並回傳 6 個模型的加權預測結果
    """
    try:
        # 1. 基礎參數提取 (從字典 req 中讀取)
        district = req.get("district", "")
        mrt_station = req.get("mrt_station", "").replace("臺", "台")
        area = float(req.get("building_area", 0))
        lat = float(req.get("latitude", 0))
        lon = float(req.get("longitude", 0))
        house_type = req.get("house_type", "大樓")

        # 2. 特徵工程 (Feature Engineering)
        
        # 行政區與捷運叢集編碼
        dist_enc = maps["dist"].get(district, 0)
        mrt_enc = maps["mrt"].get(mrt_station, 0)
        
        # 座標互動項
        coord_interact = (lat - 24.0) * (lon - 120.0)
        
        # 樓層比率
        total_f = float(req.get("total_floors", 1))
        start_f = float(req.get("start_floor", 1))
        floor_ratio = start_f / total_f if total_f > 0 else 0.5
        
        # 房屋類型 One-hot Encoding
        type_flags = {
            "type_apartment": 1 if house_type == "公寓" else 0,
            "type_building": 1 if house_type == "大樓" else 0,
            "type_mansion": 1 if house_type == "華廈" else 0,
            "type_house": 1 if house_type == "透天" else 0,
            "type_studio": 1 if house_type == "套房" else 0
        }

        # 3. 組合特徵列 (19個)
        row = {
            "building_area": area,
            "house_age": float(req.get("house_age", 0)),
            "district_enc": dist_enc,
            "mrt_cluster_enc": mrt_enc,
            "rooms": int(req.get("rooms", 0)),
            "halls": int(req.get("halls", 0)),
            "bathrooms": int(req.get("bathrooms", 0)),
            "has_parking": 1 if house_type != "公寓" else 0,
            "transaction_month": 1383, # 模型訓練基準月
            "latitude": lat,
            "longitude": lon,
            "coord_interact": coord_interact,
            "distance_to_mrt": float(req.get("distance_to_mrt", 500)),
            "floor_ratio": floor_ratio,
            **type_flags
        }

        # 轉為 NumPy 陣列
        X = np.array([[row[f] for f in FEATURES]], dtype=np.float32)

        # 4. 執行預測 (所有模型回傳的是 log1p 價格，需要 expm1 還原)
        res = {}
        for k, m in models.items():
            pred_log = float(m.predict(X)[0])
            res[k] = np.expm1(pred_log) * area

        # 5. 後處理邏輯
        # 精準開價預估 (2:7:1 加權)
        accurate_listing = (res["list_low"] * 0.2) + (res["list_mid"] * 0.7) + (res["list_high"] * 0.1)
        
        # 建議議價空間 (%)
        bargain_gap = ((accurate_listing - res["real_mid"]) / accurate_listing) * 100

        return {
            "listing_analysis": {
                "accurate_listing_price": round(accurate_listing, 0),
                "listing_range": {
                    "low": round(res["list_low"], 0),
                    "high": round(res["list_high"], 0)
                }
            },
            "real_price_reference": {
                "mid_p50": round(res["real_mid"], 0),
                "low_p10": round(res["real_low"], 0),
                "high_p90": round(res["real_high"], 0)
            },
            "insight": {
                "suggested_bargain_percent": round(max(bargain_gap, 0), 1),
                "market_hotness": "中偏熱" if bargain_gap < 5 else "穩定"
            }
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"預測運算失敗: {str(e)}")