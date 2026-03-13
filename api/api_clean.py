import pandas as pd

files = [
    "士林區.csv",
    "大同區.csv",
    "大安區.csv",
    "中山區.csv",
    "中正區.csv",
    "內湖區.csv",
    "文山區.csv",
    "北投區.csv",
    "松山區.csv",
    "信義區.csv",
    "南港區.csv",
    "萬華區.csv"
]

df = pd.concat(
    [pd.read_csv(f, encoding="utf-8-sig") for f in files],
    ignore_index=True
)

# 欄位重新命名
df = df.rename(columns={
    "objName":        "物件名稱",
    "price":          "房屋總價(萬)",
    "salePrice":      "售價",
    "style":          "型態",
    "parking":        "車位",
    "lon":            "經度",
    "lat":            "緯度",
    "landArea":       "地坪",
    "mainArea":       "主建物",
    "affiliatedArea": "附屬建坪",
})

# 清洗
df = df.drop_duplicates()
df = df.dropna(subset=["物件名稱"])

numeric_cols = ["房屋總價(萬)", "售價", "經度", "緯度", "地坪", "主建物", "附屬建坪"]
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

df["車位"] = df["車位"].fillna("無")


valid_styles = ["公寓", "大樓", "套房", "華廈", "透天"]
df = df[df["型態"].isin(valid_styles)].reset_index(drop=True)

# One-hot encoding
dummies = pd.get_dummies(df["型態"], prefix="房屋類型").reindex(
    columns=[f"房屋類型_{s}" for s in valid_styles], fill_value=0
).astype(int)
df = pd.concat([df, dummies], axis=1)

df.to_csv("merged_cleaned.csv", index=False, encoding="utf-8-sig")
print(f"完成！共 {len(df)} 筆")
