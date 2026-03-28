from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import joblib
import json
from pathlib import Path
from shapely.geometry import shape, Point

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 1. 路徑設定 (對齊你提供的 V3 路徑)
MODEL_DIR = Path("/Users/laylatang8537/Documents/vscold/projects/tpe-real-estate-ai/train/models_v3_mrt_cluster")
BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "taipei-real-estate.html"
DISTRICT_JSON_PATH = BASE_DIR / "taipei_districts.json"
MRT_JSON_PATH = BASE_DIR / "mrt_stations.json"

ANCHOR_LAT, ANCHOR_LON = 24.0, 120.0

# 資源容器
models = {}
maps = {}
districts_geometries = {}
district_centroids = {}

def load_resources():
    global models, maps, districts_geometries, district_centroids
    try:
        # A. 載入 6 組模型 (對應你上傳的檔名：low, mid, high)
        for q in ["low", "mid", "high"]:
            models[f"real_{q}"] = joblib.load(MODEL_DIR / f"lgbm_real_{q}.pkl")
            models[f"list_{q}"] = joblib.load(MODEL_DIR / f"lgbm_listing_{q}.pkl")
        
        # B. 載入地圖映射
        with open(MODEL_DIR / "mrt_cluster_map.json", "r", encoding="utf-8") as f:
            maps["mrt"] = json.load(f)
        with open(MODEL_DIR / "district_map.json", "r", encoding="utf-8") as f:
            maps["dist"] = json.load(f)
            
        # C. 載入行政區幾何
        if DISTRICT_JSON_PATH.exists():
            with open(DISTRICT_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for feat in data["features"]:
                    name = feat["properties"].get("TNAME")
                    if name:
                        poly = shape(feat["geometry"])
                        districts_geometries[name] = poly
                        district_centroids[name] = poly.centroid
        print("(・∀・) V3 資源整合載入成功")
    except Exception as e:
        print(f"(;´Д`) 載入失敗: {e}")

load_resources()

# 18 個特徵順序嚴格對齊
FEATURES = ["building_area", "house_age", "district_enc", "mrt_cluster_enc", "rooms", "halls", "bathrooms", "has_parking", "transaction_month", "latitude", "longitude", "coord_interact", "distance_to_mrt", "floor_ratio", "type_apartment", "type_building", "type_mansion", "type_house","type_studio"]

class PredictionRequest(BaseModel):
    district: str
    mrt_station: str
    building_area: float
    house_age: float
    start_floor: int
    total_floors: int
    rooms: int
    halls: int
    bathrooms: int
    latitude: float
    longitude: float
    house_type: str
    distance_to_mrt: float

@app.get("/")
async def read_index():
    if HTML_FILE.exists(): return FileResponse(HTML_FILE)
    return {"error": "HTML 檔案遺失"}

@app.get("/api/detect_district")
async def detect_district(lat: float, lon: float):
    p = Point(lon, lat)
    
    # 嚴格包含判定：完全依照 JSON 的邊界
    for name, poly in districts_geometries.items():
        if poly.contains(p):
            return {"district": name}
            
    # 只要不在這 12 個多邊形內部，一律回傳未知區域
    return {"district": "未知區域"}

@app.get("/api/mrt_data")
async def get_mrt():
    if MRT_JSON_PATH.exists(): return FileResponse(MRT_JSON_PATH)
    return []

@app.post("/api/v3/predict")
async def predict_v3(req: PredictionRequest):
    try:
        # 特徵工程與對齊
        # 字串清洗：將臺改為台以匹配 JSON Key
        mrt_name = req.mrt_station.replace("臺", "台")
        dist_enc = maps["dist"].get(req.district, 0)
        mrt_enc = maps["mrt"].get(mrt_name, 0)
        
        coord_interact = (req.latitude - ANCHOR_LAT) * (req.longitude - ANCHOR_LON)
        floor_ratio = min(max(req.start_floor / max(req.total_floors, 1), 0), 1)
        
        type_flags = {f"type_{k}": 1 if req.house_type == v else 0 
                      for k, v in [("apartment", "公寓"), ("building", "大樓"), ("mansion", "華廈"), ("house", "透天"),("studio", "套房")]}

        row = {
            "building_area": req.building_area, "house_age": req.house_age,
            "district_enc": dist_enc, "mrt_cluster_enc": mrt_enc,
            "rooms": req.rooms, "halls": req.halls, "bathrooms": req.bathrooms,
            "has_parking": 1 if req.house_type != "公寓" else 0,
            "transaction_month": 1383, "latitude": req.latitude, "longitude": req.longitude,
            "coord_interact": coord_interact, "distance_to_mrt": req.distance_to_mrt,
            "floor_ratio": floor_ratio, **type_flags
        }

        X = np.array([[row[f] for f in FEATURES]])

        # 批次推論所有模型
        res = {k: np.expm1(float(m.predict(X)[0])) * req.building_area for k, m in models.items()}

        # 加權融合算法
        accurate_listing = (res["list_low"] * 0.2) + (res["list_mid"] * 0.7) + (res["list_high"] * 0.1)
        gap = ((accurate_listing - res["real_mid"]) / accurate_listing) * 100

        return {
            "listing_analysis": {
                "accurate_listing_price": round(accurate_listing, 0),
                "listing_range": {"low": round(res["list_low"], 0), "high": round(res["list_high"], 0)}
            },
            "real_price_reference": {
                "mid_p50": round(res["real_mid"], 0),
                "low_p10": round(res["real_low"], 0),
                "high_p90": round(res["real_high"], 0)
            },
            "insight": {
                "suggested_bargain_percent": round(max(gap, 0), 1),
                "market_hotness": "高" if gap < 5 else "中" if gap < 15 else "低"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推論失敗: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)