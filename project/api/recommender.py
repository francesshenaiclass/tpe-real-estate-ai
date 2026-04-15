from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from shapely.geometry import shape, Point
import joblib, json, os, numpy as np
from pathlib import Path
from typing import List, Optional

# 1. 初始化 Router
router = APIRouter(prefix="/api/recommender", tags=["預算推薦"])

# 2. 設定路徑
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
MODEL_DIR = BASE_DIR / "models"

# ════════════════════════════════════════════════
# 3. 定義 Pydantic 資料模型 (驗收與文件化關鍵)
# ════════════════════════════════════════════════

class OptionsQuery(BaseModel):
    budget: float = Field(..., description="購屋總預算 (萬元)", example=2500)
    district: str = Field(..., description="行政區名稱", example="大安區")
    area: float = Field(..., description="預期建物坪數 (坪)", example=25.0, gt=0)
    house_age: float = Field(..., description="偏好屋齡 (年)", example=15.0, ge=0)
    mrt_dist: float = Field(..., description="可接受距離捷運站公尺數", example=500.0)
    lat: float = Field(25.04, description="中心點緯度 (地圖連動用)", example=25.0263)
    lon: float = Field(121.53, description="中心點經度 (地圖連動用)", example=121.5283)

    class Config:
        schema_extra = {
            "example": {
                "budget": 2000,
                "district": "大安區",
                "area": 20.0,
                "house_age": 10.0,
                "mrt_dist": 500,
                "lat": 25.0263,
                "lon": 121.5283
            }
        }

# 資源容器
models = {}
maps = {}
geoms = {}

# 19 個特徵順序 (嚴格對齊 V3 模型訓練順序)
FEATURES = [
    "building_area", "house_age", "district_enc", "mrt_cluster_enc", 
    "rooms", "halls", "bathrooms", "has_parking", "transaction_month", 
    "latitude", "longitude", "coord_interact", "distance_to_mrt", 
    "floor_ratio", "type_apartment", "type_building", "type_mansion", 
    "type_house", "type_studio"
]

def init():
    global models, maps, geoms
    try:
        # A. 載入分位數回歸模型
        mapping = {"p50": "lgbm_real_mid.pkl", "p10": "lgbm_real_low.pkl", "p90": "lgbm_real_high.pkl"}
        for k, f in mapping.items():
            fpath = MODEL_DIR / f
            if fpath.exists():
                tmp = joblib.load(fpath)
                models[k] = tmp.booster_ if hasattr(tmp, 'booster_') else tmp
        
        # B. 載入行政區編碼
        dist_map_path = STATIC_DIR / "district_map.json"
        if dist_map_path.exists():
            with open(dist_map_path, "r", encoding="utf-8") as f:
                maps["dist"] = json.load(f)

        # C. 載入 GIS 邊界
        dist_json_path = STATIC_DIR / "taipei_districts.json"
        if dist_json_path.exists():
            with open(dist_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for feat in data["features"]:
                    name = feat["properties"].get("TNAME")
                    if name:
                        geoms[name] = shape(feat["geometry"])
        
        print("✅ Recommender 模組資源載入成功")
    except Exception as e:
        print(f"❌ Recommender 模組載入失敗: {e}")

init()

# ════════════════════════════════════════════════
# 4. API 端點
# ════════════════════════════════════════════════

@router.get("/mrt_data", summary="獲取捷運站座標資料")
async def get_mrt():
    """回傳靜態捷運站座標 JSON 檔，用於前端地圖繪製圖釘。"""
    fpath = STATIC_DIR / "mrt_stations.json"
    if fpath.exists():
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="找不到 mrt_stations.json")

@router.get("/detect_district", summary="經緯度反查行政區")
async def detect_district(
    lat: float = Query(..., description="緯度", example=25.0422),
    lon: float = Query(..., description="經度", example=121.5327)
):
    """
    透過 Shapely GIS 運算，判斷指定的 GPS 座標屬於台北市哪一個行政區。
    這對於點擊地圖自動填入行政區功能非常有用。
    """
    p = Point(lon, lat)
    for name, poly in geoms.items():
        if poly.contains(p):
            return {"district": name}
    return {"district": "未知區域"}

@router.post("/options", summary="獲取預算匹配推薦方案")
async def get_options(q: OptionsQuery):
    """
    ## 預算推薦核心邏輯：
    1. 接收使用者輸入的行政區、預算、屋齡與坪數偏好。
    2. 系統模擬多種 **格局場景** (如：3房公寓、2房大樓)。
    3. 利用 AI 模型計算各場景在該地點的 **中位數房價 (P50)**。
    4. 篩選出 **低於使用者預算** 的方案，並提供合理議價範圍 (P10~P90)。
    """
    try:
        results = []
        dist_enc = maps.get("dist", {}).get(q.district, 0)
        
        # 基礎特徵包 (使用 Pydantic 對象 q.xxx)
        base_feat = {f: 0 for f in FEATURES}
        base_feat.update({
            "building_area": q.area, 
            "house_age": q.house_age, 
            "district_enc": dist_enc, 
            "transaction_month": 1383,
            "latitude": q.lat, 
            "longitude": q.lon,
            "coord_interact": (q.lat - 24.0) * (q.lon - 120.0), 
            "distance_to_mrt": q.mrt_dist, 
            "floor_ratio": 0.5, 
            "has_parking": 1
        })

        # 預設推薦場景
        scenarios = [
            {"name": "電梯大樓 (2房)", "f": {"type_building": 1, "rooms": 2, "halls": 1, "bathrooms": 1}},
            {"name": "家庭大樓 (3房)", "f": {"type_building": 1, "rooms": 3, "halls": 2, "bathrooms": 2}},
            {"name": "傳統公寓 (3房)", "f": {"type_apartment": 1, "rooms": 3, "halls": 2, "bathrooms": 1}},
            {"name": "精巧套房", "f": {"type_studio": 1, "rooms": 1, "halls": 1, "bathrooms": 1}}
        ]

        for s in scenarios:
            feat = base_feat.copy()
            feat.update(s["f"])
            X = np.array([[feat[f] for f in FEATURES]], dtype=np.float32)
            
            # 預測價格
            p_real_val = float(models["p50"].predict(X)[0])
            p_real = np.expm1(p_real_val) * q.area
            
            # 預算過濾
            if p_real <= q.budget:
                results.append({
                    "layout_type": s["name"],
                    "real_p50": int(p_real),
                    "real_p10": int(np.expm1(float(models["p10"].predict(X)[0])) * q.area),
                    "real_p90": int(np.expm1(float(models["p90"].predict(X)[0])) * q.area)
                })
        
        results.sort(key=lambda x: x['real_p50'], reverse=True)
        return {"results": results}

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"推薦運算失敗: {str(e)}")