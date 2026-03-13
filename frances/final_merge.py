import pandas as pd
import numpy as np

DISTRICTS = [
    "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區",
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區"
]

df = pd.read_csv("/home/frances/workspace/tpe-real-estate-ai/frances/hbhousing_csv/done/crawler_merge_all.csv", encoding="utf-8-sig")
df2 = pd.read_csv("/home/frances/workspace/tpe-real-estate-ai/frances/api/api_merge_all_data.csv", encoding="utf-8-sig")

# 讀取各區 csv 並合併成一個 df3
df3_list = []
for district in DISTRICTS:
    path = f"/home/frances/workspace/tpe-real-estate-ai/frances/api/{district}.csv"
    try:
        tmp = pd.read_csv(path, encoding="utf-8-sig")
        df3_list.append(tmp)
        print(f"✅ 讀取成功：{district}，共 {len(tmp)} 筆")
    except FileNotFoundError:
        print(f"⚠️ 找不到檔案，略過：{district}")

df3 = pd.concat(df3_list, ignore_index=True)
df3 = df3.rename(columns={
    "objName":   "物件名稱",
    "price":     "單價",
    "salePrice": "售價",
    "style":     "房屋類型",
    "parking":   "停車位",
    "lon":       "經度",
    "lat":       "緯度"
})

# 先 merge df 和 df2
df_merged = pd.merge(df, df2, on="物件名稱", how="left")
df_merged = df_merged.rename(columns={"售價": "房屋總價(萬)"})

# 刪除與 df3 重複的欄位，避免 _x _y 衝突
duplicate_cols = ["經度", "緯度", "單價", "停車位"]
df_merged = df_merged.drop(columns=[col for col in duplicate_cols if col in df_merged.columns])

# 再 merge df3
df_merged = pd.merge(df_merged, df3[["物件名稱", "單價", "停車位", "經度", "緯度"]], on="物件名稱", how="left")
print(f"merge df3 後欄位：{df_merged.columns.tolist()}")
matched = df_merged["經度"].notna().sum()
total = len(df_merged)
print(f"成功 match：{matched} 筆 / {total} 筆")

# 刪除物件名稱包含這些關鍵字的資料
keywords = ["商辦", "店面", "土地", "店辦", "車位", "辦公", "住辦"]
pattern = "|".join(keywords)
before = len(df_merged)
df_merged = df_merged[~df_merged["物件名稱"].str.contains(pattern, na=False)]
print(f"刪除關鍵字筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")

# 停車位有值的改為 1，無則為 0
df_merged["停車位"] = df_merged["停車位"].apply(lambda x: 1 if x in ["私有", "公有", "可購", "抽籤"] else 0)

# 刪除車位和單價欄位
df_merged = df_merged.drop(columns=["車位", "單價"], errors="ignore")

# 停車位改名為車位
df_merged = df_merged.rename(columns={"停車位": "車位"})

# 指定欄位順序
desired_columns = [
    "物件名稱", "路段", "行政區_中山區", "行政區_中正區", "行政區_信義區", "行政區_內湖區",
    "行政區_北投區", "行政區_南港區", "行政區_士林區", "行政區_大同區", "行政區_大安區",
    "行政區_文山區", "行政區_松山區", "行政區_萬華區", "屋齡", "建坪", "房屋總價(萬)",
    "車位", "房", "廳", "衛", "室", "有加蓋", "總樓層", "起始樓層",
    "最高樓層", "物件涵蓋層數", "房屋類型_公寓", "房屋類型_大樓", "房屋類型_套房",
    "房屋類型_華廈", "房屋類型_透天", "經度", "緯度"
]

existing_columns = [col for col in desired_columns if col in df_merged.columns]
df_merged = df_merged[existing_columns]

# 刪除任何欄位有空值的資料列
before = len(df_merged)
df_merged = df_merged.dropna()
print(f"刪除空值筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")

# 將'無'替換為 0
str_columns = ["物件名稱", "路段"]
for col in df_merged.columns:
    if col not in str_columns:
        df_merged[col] = df_merged[col].replace("無", 0)

# 處理 inf 和殘餘 NaN

df_merged = df_merged.replace([np.inf, -np.inf], np.nan)
before = len(df_merged)
df_merged = df_merged.dropna()
print(f"刪除 inf 筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")


# 數值欄位轉整數（屋齡、建坪、經度、緯度保留小數，str 欄位跳過）
float_columns = ["屋齡", "建坪", "經度", "緯度"]
skip_columns = str_columns + float_columns
for col in df_merged.columns:
    if col not in skip_columns and df_merged[col].dtype != "object":
        df_merged[col] = df_merged[col].astype(int)

df_merged.to_csv("final_merge.csv", index=False, encoding="utf-8-sig")
print(f"完成！共 {len(df_merged)} 筆")
print(df_merged.columns.tolist())