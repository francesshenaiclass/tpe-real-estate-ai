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

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
MODEL_DIR = PROJECT_ROOT / "train" / "models_v2_final"
MRT_JSON_PATH = BASE_DIR / "mrt_stations.json"
DISTRICT_JSON_PATH = BASE_DIR / "taipei_districts.json"
HTML_FILE = BASE_DIR / "taipei-real-estate.html"

districts_geometries = {}
district_centroids = {}  
m_p10 = m_p50 = m_p90 = m_list = spatial_kmeans = None
FEATURES = []
REV_DIST_MAP = {}

def load_resources():
    global m_p10, m_p50, m_p90, m_list, spatial_kmeans, FEATURES, REV_DIST_MAP, districts_geometries, district_centroids
    try:
        m_p10 = joblib.load(MODEL_DIR / "lgbm_real_p10.pkl")
        m_p50 = joblib.load(MODEL_DIR / "lgbm_real_p50.pkl")
        m_p90 = joblib.load(MODEL_DIR / "lgbm_real_p90.pkl")
        m_list = joblib.load(MODEL_DIR / "lgbm_listing_p50.pkl")
        spatial_kmeans = joblib.load(MODEL_DIR / "spatial_kmeans.pkl")
        
        with open(MODEL_DIR / "features.json", "r", encoding="utf-8") as f: 
            FEATURES = json.load(f)
        with open(MODEL_DIR / "district_map.json", "r", encoding="utf-8") as f:
            d_map = json.load(f)
            REV_DIST_MAP = {v: int(k) for k, v in d_map.items()}
        if DISTRICT_JSON_PATH.exists():
            with open(DISTRICT_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for feat in data["features"]:
                    name = feat["properties"].get("TNAME")
                    if name: 
                        poly = shape(feat["geometry"])
                        districts_geometries[name] = poly
                        district_centroids[name] = poly.centroid  
        print("所有精準資源與模型載入成功")
    except Exception as e:
        print(f"載入失敗: {e}")

load_resources()

class PredictionRequest(BaseModel):
    district: str
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
    if HTML_FILE.exists():
        return FileResponse(HTML_FILE)
    return {"error": "HTML 檔案遺失"}

@app.get("/api/detect_district")
async def detect_district(lat: float, lon: float):
    p = Point(lon, lat)
    matched = []
    
    for name, poly in districts_geometries.items():
        if poly.intersects(p.buffer(0.00005)): 
            matched.append(name)
            
    if not matched:
        return {"district": "未知區域"}
        
    if len(matched) == 1:
        return {"district": matched[0]}
        
    best_district = matched[0]
    min_dist = float('inf')
    
    for name in matched:
        dist = p.distance(district_centroids[name])
        if dist < min_dist:
            min_dist = dist
            best_district = name
            
    return {"district": best_district}

@app.get("/api/mrt_data")
async def get_mrt():
    if MRT_JSON_PATH.exists(): return FileResponse(MRT_JSON_PATH)
    return []

@app.post("/api/v3/predict")
async def predict(req: PredictionRequest):
    if m_p50 is None or spatial_kmeans is None or not FEATURES:
        raise HTTPException(status_code=503, detail="模型未就緒")

    try:
        # 回復最初的經緯度順序與直接預測邏輯
        cluster_id = spatial_kmeans.predict(np.array([[req.latitude, req.longitude]]))[0]

        row = {f: 0 for f in FEATURES}
        
        row.update({
            "building_area": req.building_area,
            "house_age": req.house_age,
            "floor_ratio": min(max(req.start_floor / max(req.total_floors, 1), 0), 1),
            "rooms": req.rooms,
            "halls": req.halls,
            "bathrooms": req.bathrooms,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "distance_to_mrt": req.distance_to_mrt, # 回復原始未除以 1000 的距離
            "area_cluster": cluster_id,
            "transaction_month": 0, # 回復原始的月份 0
            "has_parking": 1 if req.house_type != "公寓" else 0
        })

        dist_enc = REV_DIST_MAP.get(req.district)
        if dist_enc is not None:
            row["district_enc"] = dist_enc

        type_map = {"華廈": "type_mansion", "公寓": "type_apartment", "透天": "type_house", "大樓": "type_building"}
        target_col = type_map.get(req.house_type)
        if target_col in row:
            row[target_col] = 1

        X = np.array([[row[f] for f in FEATURES]])

        def calculate_price(model):
            log_price_pred = float(model.predict(X)[0])
            unit_price = np.expm1(log_price_pred)
            return unit_price * req.building_area

        p10_total = calculate_price(m_p10)
        p50_total = calculate_price(m_p50)
        p90_total = calculate_price(m_p90)
        list_total = calculate_price(m_list)

        raw_gap = ((list_total - p50_total) / p50_total) * 100
        if raw_gap > 25:
            calibrated_gap = 20 + (raw_gap - 25) * 0.15
        elif raw_gap < 5:
            calibrated_gap = 8 + raw_gap * 0.1
        else:
            calibrated_gap = raw_gap

        return {
            "price_results": {
                "market_listing_total": round(list_total, 0),
                "total_price_mid": round(p50_total, 0),
                "safety_range": {
                    "low_p10": round(p10_total, 0),
                    "high_p90": round(p90_total, 0)
                }
            },
            "analysis": {
                "bargain_space_percent": round(calibrated_gap, 1),
                "area_cluster_id": int(cluster_id)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)