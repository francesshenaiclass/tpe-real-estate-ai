import pandas as pd
import numpy as np

DISTRICTS = [
    "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區",
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區"
]

df = pd.read_csv("/home/frances/tpe-real-estate-ai/frances/hbhousing_csv/crawler_merge_all.csv", encoding="utf-8-sig")
df2 = pd.read_csv("/home/frances/tpe-real-estate-ai/frances/api/api_merge_all_data.csv", encoding="utf-8-sig")

df3_list = []
for district in DISTRICTS:
    path = f"/home/frances/tpe-real-estate-ai/frances/api/{district}.csv"
    try:
        tmp = pd.read_csv(path, encoding="utf-8-sig")
        df3_list.append(tmp)
        print(f"✅ 讀取成功：{district}，共 {len(tmp)} 筆")
    except FileNotFoundError:
        print(f"⚠️ 找不到檔案，略過：{district}")

df3 = pd.concat(df3_list, ignore_index=True)
df3 = df3.rename(columns={"objName":"物件名稱","price":"單價","salePrice":"售價","style":"房屋類型","parking":"停車位","lon":"經度","lat":"緯度"})

df_merged = pd.merge(df, df2, on="物件名稱", how="left")
df_merged = df_merged.rename(columns={"售價": "房屋總價(萬)"})

duplicate_cols = ["經度", "緯度", "單價", "停車位"]
df_merged = df_merged.drop(columns=[col for col in duplicate_cols if col in df_merged.columns])

df_merged = pd.merge(df_merged, df3[["物件名稱", "單價", "停車位", "經度", "緯度"]], on="物件名稱", how="left")
print(f"merge df3 後欄位：{df_merged.columns.tolist()}")
matched = df_merged["經度"].notna().sum()
print(f"成功 match：{matched} 筆 / {len(df_merged)} 筆")

keywords = ["商辦", "店面", "土地", "店辦", "車位", "辦公", "住辦"]
pattern = "|".join(keywords)
before = len(df_merged)
df_merged = df_merged[~df_merged["物件名稱"].str.contains(pattern, na=False)]
print(f"刪除關鍵字筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")

df_merged["停車位"] = df_merged["停車位"].apply(lambda x: 1 if x in ["私有", "公有", "可購", "抽籤"] else 0)
df_merged = df_merged.drop(columns=["車位", "單價"], errors="ignore")
df_merged = df_merged.rename(columns={"停車位": "車位"})

district_cols = [col for col in df_merged.columns if col.startswith("行政區_")]
df_merged["行政區"] = df_merged[district_cols].idxmax(axis=1).str.replace("行政區_", "")

desired_columns = [
    "行政區", "路段", "緯度", "經度",
    "行政區_中正區", "行政區_大同區", "行政區_中山區", "行政區_松山區",
    "行政區_大安區", "行政區_萬華區", "行政區_信義區", "行政區_士林區",
    "行政區_北投區", "行政區_內湖區", "行政區_南港區", "行政區_文山區",
    "屋齡", "建坪", "房屋總價(萬)", "車位", "房", "廳", "衛", "室",
    "有加蓋", "總樓層", "起始樓層", "最高樓層", "物件涵蓋層數",
    "房屋類型_公寓", "房屋類型_大樓", "房屋類型_套房", "房屋類型_華廈", "房屋類型_透天"
]
existing_columns = [col for col in desired_columns if col in df_merged.columns]
df_merged = df_merged[existing_columns]

before = len(df_merged)
df_merged = df_merged.dropna()
print(f"刪除空值筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")

str_columns = ["行政區", "路段"]
for col in df_merged.columns:
    if col not in str_columns:
        df_merged[col] = df_merged[col].replace("無", 0)

df_merged = df_merged.replace([np.inf, -np.inf], np.nan)
before = len(df_merged)
df_merged = df_merged.dropna()
print(f"刪除 inf 筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")

# 刪除屋齡 <= -1 的資料
before = len(df_merged)
df_merged = df_merged[df_merged["屋齡"] > -1]
print(f"刪除屋齡 <= -1 筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")
 
# 刪除房 > 10 的資料
before = len(df_merged)
df_merged = df_merged[df_merged["房"] <= 10]
print(f"刪除房 > 10 筆數：{before - len(df_merged)} 筆，剩餘 {len(df_merged)} 筆")


float_columns = ["屋齡", "建坪", "經度", "緯度"]
for col in df_merged.columns:
    if col in float_columns:
        continue
    try:
        df_merged[col] = pd.to_numeric(df_merged[col], errors="raise").astype(int)
    except (ValueError, TypeError):
        continue

df_merged.to_csv("final_merge.csv", index=False, encoding="utf-8-sig")
print(f"完成！共 {len(df_merged)} 筆")
print(df_merged.columns.tolist())

