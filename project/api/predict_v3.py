from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import numpy as np
import joblib, json
from pathlib import Path

# 1. 初始化 Router
router = APIRouter(prefix="/api/predict", tags=["AI 精準預估"])

# 2. 設定路徑
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

# ════════════════════════════════════════════════
# 3. 定義 Pydantic 資料模型 
# ════════════════════════════════════════════════
class PredictReq(BaseModel):
    district: str = Field(..., description="行政區名稱", example="中正區")
    mrt_station: str = Field(..., description="最近捷運站名稱", example="台北車站")
    building_area: float = Field(..., description="建物總坪數 (坪)", example=25.5, gt=0)
    latitude: float = Field(..., description="地理緯度", example=25.0348)
    longitude: float = Field(..., description="地理經度", example=121.5291)
    house_type: Literal["公寓", "大樓", "華廈", "透天", "套房"] = Field(
        "大樓", description="房屋類型", example="大樓"
    )
    house_age: float = Field(0, description="屋齡 (年)", example=15.0, ge=0)
    total_floors: int = Field(12, description="建物總層數", example=12, gt=0)
    start_floor: int = Field(5, description="欲查詢樓層", example=5)
    rooms: int = Field(2, description="房間數", example=2)
    halls: int = Field(1, description="廳數", example=1)
    bathrooms: int = Field(1, description="衛浴數", example=1)
    distance_to_mrt: float = Field(500.0, description="距離捷運站公尺數", example=300.0)

    class Config:
        schema_extra = {
            "example": {
                "district": "中正區",
                "mrt_station": "台北車站",
                "building_area": 25.5,
                "latitude": 25.0348,
                "longitude": 121.5291,
                "house_type": "大樓",
                "house_age": 15.0,
                "total_floors": 12,
                "start_floor": 5,
                "rooms": 2,
                "halls": 1,
                "bathrooms": 1,
                "distance_to_mrt": 300.0
            }
        }

# 資源容器
models = {}
maps = {}

def init():
    global models, maps
    try:
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
                models[key] = tmp.booster_ if hasattr(tmp, 'booster_') else tmp
        
        with open(STATIC_DIR / "district_map.json", "r", encoding="utf-8") as f:
            maps["dist"] = json.load(f)
        with open(STATIC_DIR / "mrt_cluster_map.json", "r", encoding="utf-8") as f:
            maps["mrt"] = json.load(f)
            
        print("✅ Predict V3 模組資源載入成功")
    except Exception as e:
        print(f"❌ Predict V3 模組載入失敗: {e}")

init()

# ════════════════════════════════════════════════
# 4. API 端點 (已改為 PredictReq)
# ════════════════════════════════════════════════

@router.post("/v3", summary="執行 AI 房價精準預估")
async def do_predict(req: PredictReq):
    """
    ##  AI 房價預估核心邏輯
    本端點整合 **LightGBM 分位數回歸模型**，針對台北市房價進行深度預測：

    1. **特徵工程處理**：自動將「行政區」與「捷運站」轉換為模型可識別的編碼，並計算「樓層比率」與「座標互動項」。
    2. **多模型平行運算**：同時啟動 6 個模型，包含：
        - **實價登錄模型** (Real Price)：預估成交中位數 P50、低標 P10、高標 P90。
        - **市場開價模型** (Listing Price)：預估開價中位數與範圍。
    3. **議價空間分析**：計算開價與實價之間的差距，提供「建議議價比例」與「市場熱度」建議。

    ---
    ###  輸入說明
    - 請參考下方的 **Request Body** 架構。
    - **house_type**：支援 公寓、大樓、華廈、透天、套房。
    - **building_area**：請輸入權狀總坪數。

    ###  輸出價值
    - **精準開價**：幫助買賣雙方設定合理的起始價格。
    - **行情參考**：提供該物件在實價登錄中的落點預測。
    """
    try:
        # 1. 特徵工程 (使用物件點選方式 req.xxx)
        district = req.district
        mrt_station = req.mrt_station.replace("臺", "台")
        
        dist_enc = maps["dist"].get(district, 0)
        mrt_enc = maps["mrt"].get(mrt_station, 0)
        
        # 座標互動項
        coord_interact = (req.latitude - 24.0) * (req.longitude - 120.0)
        
        # 樓層比率 (防呆)
        floor_ratio = req.start_floor / req.total_floors if req.total_floors > 0 else 0.5
        
        # 房屋類型 One-hot
        type_flags = {
            "type_apartment": 1 if req.house_type == "公寓" else 0,
            "type_building": 1 if req.house_type == "大樓" else 0,
            "type_mansion": 1 if req.house_type == "華廈" else 0,
            "type_house": 1 if req.house_type == "透天" else 0,
            "type_studio": 1 if req.house_type == "套房" else 0
        }

        # 2. 組合 19 個特徵列
        row = {
            "building_area": req.building_area,
            "house_age": req.house_age,
            "district_enc": dist_enc,
            "mrt_cluster_enc": mrt_enc,
            "rooms": req.rooms,
            "halls": req.halls,
            "bathrooms": req.bathrooms,
            "has_parking": 1 if req.house_type != "公寓" else 0,
            "transaction_month": 1383, 
            "latitude": req.latitude,
            "longitude": req.longitude,
            "coord_interact": coord_interact,
            "distance_to_mrt": req.distance_to_mrt,
            "floor_ratio": floor_ratio,
            **type_flags
        }

        # 轉為 NumPy 並執行預測
        X = np.array([[row[f] for f in FEATURES]], dtype=np.float32)

        res = {}
        for k, m in models.items():
            pred_log = float(m.predict(X)[0])
            res[k] = np.expm1(pred_log) * req.building_area

        # 3. 後處理分析
        # 精準開價預估 (2:7:1 加權模型)
        accurate_listing = (res["list_low"] * 0.2) + (res["list_mid"] * 0.7) + (res["list_high"] * 0.1)
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