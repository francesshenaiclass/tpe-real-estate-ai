import requests
import pandas as pd
import zipfile
import io
import re
from datetime import datetime

print("開始下載近一年實價登錄資料...")

seasons = ["113S4","113S3","113S2","113S1"]

all_data = []

# -----------------------
# 下載資料
# -----------------------
for season in seasons:

    print("下載:", season)

    url = f"https://plvr.land.moi.gov.tw/DownloadSeason?season={season}&type=zip&fileName=lvr_landcsv.zip"

    response = requests.get(url)

    z = zipfile.ZipFile(io.BytesIO(response.content))

    df = pd.read_csv(z.open("a_lvr_land_a.csv"))

    df = df.iloc[1:]

    all_data.append(df)

print("資料下載完成")

df = pd.concat(all_data, ignore_index=True)

print("資料合併完成")

# -----------------------
# 基本資料清洗
# -----------------------

df = df[df["建築完成年月"].notna()]
df = df[df["主要用途"] == "住家用"]

df["總價元"] = pd.to_numeric(df["總價元"], errors="coerce")
df["單價元平方公尺"] = pd.to_numeric(df["單價元平方公尺"], errors="coerce")
df["建物移轉總面積平方公尺"] = pd.to_numeric(df["建物移轉總面積平方公尺"], errors="coerce")

# -----------------------
# 計算坪數與價格
# -----------------------

df["建坪"] = df["建物移轉總面積平方公尺"] / 3.3058
df["每坪價格"] = df["單價元平方公尺"] * 3.3058

# -----------------------
# 屋齡
# -----------------------

current_year = datetime.now().year

def calc_age(x):
    try:
        year = int(str(x)[:3]) + 1911
        return current_year - year
    except:
        return None

df["屋齡"] = df["建築完成年月"].apply(calc_age)

# -----------------------
# 房屋格局
# -----------------------

df["房"] = pd.to_numeric(df["建物現況格局-房"], errors="coerce")
df["廳"] = pd.to_numeric(df["建物現況格局-廳"], errors="coerce")
df["衛"] = pd.to_numeric(df["建物現況格局-衛"], errors="coerce")

# -----------------------
# 車位數量
# -----------------------

def parking_count(x):

    try:
        match = re.search(r"車位(\d+)", str(x))

        if match:
            return int(match.group(1))

        return 0

    except:
        return 0

df["車位數量"] = df["交易筆棟數"].apply(parking_count)

# -----------------------
# 是否加蓋
# -----------------------

def has_extension(x):

    if pd.isna(x):
        return 0

    keywords = ["加蓋","外推","增建"]

    for k in keywords:
        if k in str(x):
            return 1

    return 0

df["是否加蓋"] = df["備註"].apply(has_extension)

# -----------------------
# 房屋類型
# -----------------------

def house_type(x):

    if pd.isna(x):
        return None

    x = str(x)

    if "公寓" in x:
        return "公寓"
    elif "住宅大樓" in x:
        return "大樓"
    elif "華廈" in x:
        return "華廈"
    elif "透天" in x:
        return "透天"
    else:
        return None

df["房屋類型"] = df["建物型態"].apply(house_type)

# -----------------------
# 過濾異常資料
# -----------------------

df = df[(df["每坪價格"] > 50000) & (df["每坪價格"] < 2000000)]
df = df[(df["建坪"] > 5) & (df["建坪"] < 200)]
df = df[(df["屋齡"] >= 0) & (df["屋齡"] < 100)]

# -----------------------
# 建立輸出資料
# -----------------------

result = pd.DataFrame()

# 行政區 One-Hot
districts = [
"中山區","中正區","信義區","內湖區","北投區","南港區",
"士林區","大同區","大安區","文山區","松山區","萬華區"
]

for d in districts:
    result[f"行政區_{d}"] = (df["鄉鎮市區"] == d).astype(int)

# 基本資料
result["建坪"] = df["建坪"].round(2)
result["房屋總價"] = df["總價元"]
result["單位"] = df["每坪價格"].round(0)

result["房"] = df["房"]
result["廳"] = df["廳"]
result["衛"] = df["衛"]

result["車位數量"] = df["車位數量"]
result["是否加蓋"] = df["是否加蓋"]

# 房屋類型 One-Hot
types = ["公寓","大樓","華廈","透天"]

for t in types:
    result[f"房屋類型_{t}"] = (df["房屋類型"] == t).astype(int)

# -----------------------
# 固定欄位順序
# -----------------------

columns_order = [

"行政區_中山區","行政區_中正區","行政區_信義區","行政區_內湖區",
"行政區_北投區","行政區_南港區","行政區_士林區","行政區_大同區",
"行政區_大安區","行政區_文山區","行政區_松山區","行政區_萬華區",

"建坪","房屋總價","單位","房","廳","衛",
"車位數量","是否加蓋",

"房屋類型_公寓","房屋類型_大樓",
"房屋類型_華廈","房屋類型_透天"

]

result = result[columns_order]

# -----------------------
# 輸出CSV
# -----------------------

result = result.dropna()

result.to_csv("taipei_house_data.csv", index=False, encoding="utf-8-sig")

print("完成！輸出檔案 taipei_house_data.csv")