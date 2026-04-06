# 台北市房價預測系統

此系統提供台北市房價合理區間預測，整合現售價與實價登錄資料，提供三支 RESTful API。

---

## 系統架構
project/
├── train_v3.py                    # 訓練腳本（預測模型）
├── main.py                        # FastAPI 主程式（三支 API）
├── requirements.txt               # Python所需的套件清單
├── api/                           # 訓練產出的模型檔案
│   ├── market_trends.py           # 市場趨勢 API
│   ├── predict_v3.py              # 預測 API
│   └── recommender.py             # 推薦API
├── models/                        # 訓練產出的模型檔案
│   ├── lgbm_listing_high.pkl      # 掛牌價預測模型（高標 P90，代表市場開價上限）
│   ├── lgbm_listing_mid.pkl       # 掛牌價預測模型（中標 P50，代表市場開價中位數）
│   ├── lgbm_listing_low.pkl       # 掛牌價預測模型（低標 P10，代表市場開價下限）
│   ├── lgbm_real_high.pkl         # 成交價預測模型（高標 P90，代表成交行情上限）
│   ├── lgbm_real_mid.pkl          # 成交價預測模型（中標 P50，代表成交行情中位數）
│   └── lgbm_real_low.pkl          # 成交價預測模型（低標 P10，代表成交行情下限）
├── static/                        # 靜態資源與地理資訊
│   ├── district_map.json          # 行政區
│   ├── mrt_cluster_map.json       # 捷運站名稱編碼
│   ├── mrt_stations.json          # 捷運站出口精確座標
│   └── taipei_districts.json      # 行政區地理邊界
├── templates/                     # 前端畫面模板
│   ├── index.html                 # 主畫面
│   ├── page_predict.html          # 預測分頁
│   ├── page_recommend.html        # 推薦分頁
│   └── page_trends.html           # 趨勢分頁
└── data/                           
    ├── house_prediction_data.csv  # 現售價資料
    ├── mrt_distance.csv           # 捷運站經緯度資料  
    └── house_prices_taipei.csv    # 實價登錄資料


---

## 模型說明

本系統使用 **LightGBM 分位數回歸**，分別對「實價登錄成交資料」與「現售掛牌資料」各訓練三個模型，共六個模型。

### 訓練資料來源

| 資料集 | 說明 |
|--------|------|
| `house_prices_taipei.csv` | 實價登錄歷史成交資料 |
| `house_prediction_data.csv` | 現售房屋掛牌資料 |

### 預測目標

以「每坪單價（元）」作為預測目標，訓練時對單價取 `log1p()` 轉換以穩定分佈，預測完畢後以 `expm1()` 還原。

### 模型種類

每份資料各訓練三個分位數模型：

| 模型 | Alpha | 說明 |
|------|-------|------|
| low  | P10   | 市場低標，低於此價格的僅佔 10% |
| mid  | P50   | 市場中位數，最具參考性的合理行情 |
| high | P90   | 市場高標，高於此價格的僅佔 10% |

### 輸入特徵（14個）

| 類別 | 特徵 |
|------|------|
| 房屋基本 | `building_area`、`house_age`、`rooms`、`halls`、`bathrooms`、`has_parking`、`floor_ratio` |
| 地理位置 | `latitude`、`longitude`、`coord_interact`、`distance_to_mrt` |
| 類別編碼 | `district_enc`（行政區）、`mrt_cluster_enc`（最近捷運站） |
| 時間 | `transaction_month` |
| 房型 | `type_apartment`、`type_building`、`type_mansion`、`type_house`、`type_studio` |


---

## 環境安裝
**Python 版本需求：** Python 3.9 以上

1. 複製專案
bash
```
git clone <your-repo-url>
cd tpe-real-estate-ai
```

2. 安裝套件
bash
```
pip install -r requirements.txt
```
---

## 訓練模型
若需要重新訓練模型，執行以下指令：
bash
```
python train_v3.py
```

訓練完成後會自動將模型輸出至 `models/` 目錄，並產生以下對照表供 API 使用：
models/
├── lgbm_real_low.pkl
├── lgbm_real_mid.pkl
├── lgbm_real_high.pkl
├── lgbm_listing_low.pkl
├── lgbm_listing_mid.pkl
├── lgbm_listing_high.pkl
├── district_map.json        # 行政區名稱 → 編碼數字
└── mrt_cluster_map.json     # 捷運站名稱 → 編碼數字

訓練結束後終端機會輸出各模型的預測誤差（MAPE）與前六大特徵重要性，可作為模型品質參考。



