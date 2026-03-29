from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from shapely.geometry import shape, Point
import joblib, json, os, numpy as np
from pathlib import Path

# 1. 初始化 Router
router = APIRouter(prefix="/api/recommender", tags=["預算推薦"])

# 2. 設定路徑 (project/api/recommender.py -> project/)
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
MODEL_DIR = BASE_DIR / "models"

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
        # A. 載入 p50, p10, p90 推薦模型
        mapping = {
            "p50": "lgbm_real_mid.pkl", 
            "p10": "lgbm_real_low.pkl", 
            "p90": "lgbm_real_high.pkl"
        }
        for k, f in mapping.items():
            fpath = MODEL_DIR / f
            if fpath.exists():
                tmp = joblib.load(fpath)
                # 提取 Booster 核心
                models[k] = tmp.booster_ if hasattr(tmp, 'booster_') else tmp
        
        # B. 載入行政區編碼圖
        dist_map_path = STATIC_DIR / "district_map.json"
        if dist_map_path.exists():
            with open(dist_map_path, "r", encoding="utf-8") as f:
                maps["dist"] = json.load(f)

        # C. 載入 GIS 邊界 (用於 detect_district)
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
# API 端點
# ════════════════════════════════════════════════

@router.get("/mrt_data")
async def get_mrt():
    """回傳捷運站座標 JSON"""
    fpath = STATIC_DIR / "mrt_stations.json"
    if fpath.exists():
        return FileResponse(fpath)
    raise HTTPException(status_code=404, detail="找不到 mrt_stations.json")

@router.get("/detect_district")
async def detect_district(lat: float, lon: float):
    """根據經緯度判定行政區 (修正 404 問題)"""
    p = Point(lon, lat)
    for name, poly in geoms.items():
        if poly.contains(p):
            return {"district": name}
    return {"district": "未知區域"}

@router.post("/options")
async def get_options(q: dict):
    """根據預算推薦不同的房屋格局方案"""
    try:
        results = []
        # 取得行政區編碼 (預設 0)
        dist_enc = maps.get("dist", {}).get(q['district'], 0)
        lat = q.get('lat', 25.04)
        lon = q.get('lon', 121.53)
        
        # 基礎特徵包
        base_feat = {f: 0 for f in FEATURES}
        base_feat.update({
            "building_area": q['area'], 
            "house_age": q['house_age'], 
            "district_enc": dist_enc, 
            "transaction_month": 1383, # 基準月份
            "latitude": lat, 
            "longitude": lon,
            "coord_interact": (lat - 24.0) * (lon - 120.0), 
            "distance_to_mrt": q['mrt_dist'], 
            "floor_ratio": 0.5, 
            "has_parking": 1
        })

        # 測試格局場景
        scenarios = [
            {"name": "電梯大樓 (2房)", "f": {"type_building": 1, "rooms": 2, "halls": 1, "bathrooms": 1}},
            {"name": "家庭大樓 (3房)", "f": {"type_building": 1, "rooms": 3, "halls": 2, "bathrooms": 2}},
            {"name": "傳統公寓 (3房)", "f": {"type_apartment": 1, "rooms": 3, "halls": 2, "bathrooms": 1}},
            {"name": "精巧套房", "f": {"type_studio": 1, "rooms": 1, "halls": 1, "bathrooms": 1}}
        ]

        for s in scenarios:
            feat = base_feat.copy()
            feat.update(s["f"])
            # 轉換為 NumPy 陣列進行預測
            X = np.array([[feat[f] for f in FEATURES]], dtype=np.float32)
            
            # 計算 P50 成交價
            p_real_val = float(models["p50"].predict(X)[0])
            p_real = np.expm1(p_real_val) * q['area']
            
            # 如果在預算內，則加入推薦清單
            if p_real <= q['budget']:
                results.append({
                    "layout_type": s["name"],
                    "real_p50": int(p_real),
                    "real_p10": int(np.expm1(float(models["p10"].predict(X)[0])) * q['area']),
                    "real_p90": int(np.expm1(float(models["p90"].predict(X)[0])) * q['area'])
                })
        
        # 依價格由高到低排序
        results.sort(key=lambda x: x['real_p50'], reverse=True)
        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推薦運算失敗: {str(e)}")