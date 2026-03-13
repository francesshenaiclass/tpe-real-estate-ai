import pandas as pd
import re

DISTRICT_MAP = [
    "中正區", "大同區", "中山區", "松山區", "大安區", "萬華區", 
    "信義區", "士林區", "北投區", "內湖區", "南港區", "文山區",
]
FINAL_COLUMNS = [
    '物件名稱', '售價','經度','緯度','屋齡'
]

COLUMN_RENAME_MAP = {
    'objName':        '物件名稱',
    'price':          '價格',
    'salePrice':      '售價',
    'style':          '風格',
    'parking':        '停車位',
    'lon':            '經度',
    'lat':            '緯度',
    'landArea':       '土地面積',
    'mainArea':       '主建物面積',
    'affiliatedArea': '附屬建物面積',
    'zipCode':        '郵遞區號',
    'age':            '屋齡',
}

# 讀取主要資料
all_df_list = []
for district in DISTRICT_MAP:
    file_path = f'/home/frances/workspace/tpe-real-estate-ai/frances/api/{district}.csv'
    try:
        df = pd.read_csv(file_path)
        df['行政區'] = district
        all_df_list.append(df)
    except Exception as e:
        print(f"跳過 {district}: {e}")

raw_df = pd.concat(all_df_list, ignore_index=True)

# --- rename 前：全部用英文欄位操作 ---

# 過濾非住宅類型（用英文欄位 style）
exclude_keywords = '店面|辦公|工作室|土地|車位|廠房|倉庫|商辦|地下室'
raw_df = raw_df[~raw_df['style'].str.contains(exclude_keywords, na=False)]


# 行政區 one-hot encoding
for d in DISTRICT_MAP:
    raw_df[f'行政區_{d}'] = (raw_df['行政區'] == d).astype(int)

# 車位、有加蓋（用英文欄位 objName）
raw_df['車位'] = raw_df['objName'].apply(lambda x: 1 if '車位' in str(x) else 0)
raw_df['有加蓋'] = raw_df['objName'].apply(lambda x: 1 if '頂加' in str(x) or '加蓋' in str(x) else 0)

# 讀取含 objName, age 的補充檔案並以原始英文欄位合併
age_df_list = []
for district in DISTRICT_MAP:
    file_path = f'/home/frances/workspace/tpe-real-estate-ai/frances/api/{district}-age.csv'  
    try:
        df = pd.read_csv(file_path)
        age_df_list.append(df)
    except Exception as e:
        print(f"跳過 age 檔案 {district}: {e}")

if age_df_list:
    age_df = pd.concat(age_df_list, ignore_index=True)
    raw_df = raw_df.merge(age_df[['objName', 'age']], on='objName', how='left')
else:
    raw_df['age'] = None

# --- rename 後：統一轉換成中文欄位名稱 ---
raw_df = raw_df.rename(columns=COLUMN_RENAME_MAP)

final_df = raw_df.reindex(columns=FINAL_COLUMNS).fillna(0)
final_df.drop_duplicates(inplace=True)

final_df.to_csv('api_merge_all_data.csv', index=False, encoding='utf-8-sig')
print(f"處理完成，總住宅筆數：{len(final_df)}")