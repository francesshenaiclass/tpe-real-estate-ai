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
MODEL_PATH = BASE_DIR.parent / "train" / "models_v2"
HTML_FILE = "taipei-real-estate.html"

# 全域資源
districts_geometries = {}
m_p10 = m_p50 = m_p90 = m_list = None
FEATURES = []
REV_DIST_MAP = {}

def load_resources():
    global m_p10, m_p50, m_p90, m_list, FEATURES, REV_DIST_MAP, districts_geometries
    try:
        m_p10 = joblib.load(MODEL_PATH / "lgbm_real_p10.pkl")
        m_p50 = joblib.load(MODEL_PATH / "lgbm_real_p50.pkl")
        m_p90 = joblib.load(MODEL_PATH / "lgbm_real_p90.pkl")
        m_list = joblib.load(MODEL_PATH / "lgbm_listing_p50.pkl")
        with open(MODEL_PATH / "features.json", "r", encoding="utf-8") as f: FEATURES = json.load(f)
        with open(MODEL_PATH / "district_map.json", "r", encoding="utf-8") as f:
            d_map = json.load(f)
            REV_DIST_MAP = {v: int(k) for k, v in d_map.items()}
        with open(BASE_DIR / "taipei_districts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for feat in data["features"]:
                name = feat["properties"].get("TNAME")
                districts_geometries[name] = shape(feat["geometry"])
        print("✅ 資源載入成功")
    except Exception as e: print(f"Error: {e}")

load_resources()

@app.get("/")
async def read_index():
    return FileResponse(BASE_DIR / HTML_FILE)

@app.get("/api/detect_district")
async def detect_district(lat: float, lon: float):
    p = Point(lon, lat)
    # 這裡的迴圈順序決定了重疊區的歸屬，大安區應排在前面
    for name, poly in districts_geometries.items():
        if poly.contains(p): return {"district": name}
    return {"district": "未知區域"}

@app.get("/api/mrt_data")
async def get_mrt():
    with open(BASE_DIR / "mrt_stations.json", "r", encoding="utf-8") as f: return json.load(f)

class PredictRequest(BaseModel):
    district: str
    building_area: float
    house_age: float
    start_floor: int
    total_floors: int
    latitude: float
    longitude: float
    house_type: str
    distance_to_mrt: float
    rooms: int
    halls: int
    bathrooms: int

@app.post("/api/v3/predict")
def predict(req: PredictRequest):
    dist_enc = REV_DIST_MAP.get(req.district)
    if dist_enc is None: raise HTTPException(status_code=400, detail="不支援行政區")

    row = {f: 0 for f in FEATURES}
    row.update({
        "building_area": req.building_area, "house_age": req.house_age,
        "floor_ratio": req.start_floor / max(req.total_floors, 1),
        "district_enc": dist_enc, "latitude": req.latitude, "longitude": req.longitude,
        "distance_to_mrt": req.distance_to_mrt,
        "rooms": req.rooms, "halls": req.halls, "bathrooms": req.bathrooms
    })
    
    type_map = {"華廈": "type_mansion", "公寓": "type_apartment", "套房": "type_studio", "透天": "type_house", "大樓": "type_building"}
    row[type_map.get(req.house_type, "type_building")] = 1
    X = np.array([[row[f] for f in FEATURES]])
    def gv(m): return float(np.expm1(m.predict(X)[0]))
    
    p10, p50, p90, lv = gv(m_p10), gv(m_p50), gv(m_p90), gv(m_list)
    
    # --- 數據校準邏輯 ---
    raw_gap = ((lv - p50) / p50) * 100
    if raw_gap > 25:
        calibrated_gap = 20 + (raw_gap - 25) * 0.15 # 壓縮極端溢價
    elif raw_gap < 5:
        calibrated_gap = 8 + raw_gap * 0.1
    else:
        calibrated_gap = raw_gap

    return {
        "price_results": {
            "market_listing_total": round(lv * req.building_area, 0),
            "total_price_mid": round(p50 * req.building_area, 0),
            "safety_range": {
                "low_p10": round(p10 * req.building_area, 0),
                "high_p90": round(p90 * req.building_area, 0)
            }
        },
        "analysis": { "bargain_space_percent": round(calibrated_gap, 1) }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)