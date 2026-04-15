import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

tags_metadata = [
    {
        "name": "AI 精準預估",
        "description": "包含房價分位數回歸模型 (P10, P50, P90)，提供市場成交價格區間預測。",
    },
    {
        "name": "預算推薦",
        "description": "基於地理空間分析與使用者財務預算，提供個人化的置產組合建議。",
    },
    {
        "name": "市場趨勢分析",
        "description": "整合實價登錄大數據，呈現台北市各區房價成長率與市場健康指標。",
    },
    {
        "name": "頁面導覽",
        "description": "提供前端 HTML 頁面的渲染入口。",
    }
]

# 1. 確定專案根目錄
BASE_DIR = Path(__file__).resolve().parent

# 2. 強化的安全匯入機制
# 這樣改可以確保：即使其中一個組員的 API 壞了，主程式依然能跑，並告訴你是誰壞了
predict_v3 = recommender = market_trends = None

try:
    from api import predict_v3
    print("✅ [模組 A] 精準預估 (predict_v3) 載入成功")
except Exception as e:
    print(f"❌ [模組 A] 載入失敗: {e}")

try:
    from api import recommender
    print("✅ [模組 B] 預算推薦 (recommender) 載入成功")
except Exception as e:
    print(f"❌ [模組 B] 載入失敗: {e}")

try:
    from api import market_trends
    print("✅ [模組 C] 趨勢分析 (market_trends) 載入成功")
except Exception as e:
    print(f"❌ [模組 C] 載入失敗: {e}")

# --- 核心初始化 (開啟 debug 模式) ---
app = FastAPI(
    title="台北房產大數據決策平台",
    description="""
    本平台旨在解決台北市購屋資訊不對稱問題，透過爬蟲抓取四大資料源，建立分群與預測模型。
    
     技術規格：FastAPI + LightGBM + MySQL + GCP Cloud SQL
     主要功能：AI 房價預估、置產建議、房價趨勢 
     開發團隊：組長 Frances 與其AI決策團隊
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",  
    redoc_url="/redoc",
    debug=True
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# 3. 掛載靜態檔案與檢查
static_path = BASE_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    print(f"📂 靜態資源掛載成功: {static_path}")
else:
    print(f"⚠️ 找不到 static 資料夾: {static_path}")

# 設定模板路徑
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 4. 註冊 API 路由
if predict_v3 and hasattr(predict_v3, 'router'):
    app.include_router(predict_v3.router)
if recommender and hasattr(recommender, 'router'):
    app.include_router(recommender.router)
if market_trends and hasattr(market_trends, 'router'):
    app.include_router(market_trends.router)

# 5.頁面導覽路由 (Tags 設為頁面導覽)
@app.get("/", tags=["頁面導覽"])
async def portal(request: Request):
    """主首頁入口"""
    return templates.TemplateResponse(request=request, name="index.html")
# 補上這一段
@app.get("/pages/architecture")
async def get_architecture(request: Request):
    return templates.TemplateResponse(request=request, name="architecture.html")

@app.get("/pages/predict", tags=["頁面導覽"])
async def get_predict(request: Request):
    """AI 房價預估頁面"""
    return templates.TemplateResponse(request=request, name="page_predict.html")

@app.get("/pages/recommend", tags=["頁面導覽"])
async def get_recommend(request: Request):
    """置產建議頁面"""
    return templates.TemplateResponse(request=request, name="page_recommend.html")

@app.get("/pages/trends", tags=["頁面導覽"])
async def get_trends(request: Request):
    """房價漲幅趨勢頁面"""
    return templates.TemplateResponse(request=request, name="page_trends.html")

# 6. 自定義 404 錯誤處理
@app.exception_handler(404)
async def custom_404_handler(request: Request, __):
    return JSONResponse(
        status_code=404, 
        content={"message": "路徑或 HTML 檔案找不到，請確認 templates 資料夾內容。"}
    )

if __name__ == "__main__":
    print("="*60)
    print("🚀 系統啟動中...")
    print(f"🏠 主頁入口: http://127.0.0.1:8005")
    print(f"📑 API 文檔: http://127.0.0.1:8005/docs")
    print("="*60)
    uvicorn.run(app, host="127.0.0.1", port=8005)