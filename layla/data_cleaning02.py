import pandas as pd
import os

# 🌟 新增 GPS 定位：抓取這個 data_cleaning02.py 所在的「絕對路徑」
base_dir = os.path.dirname(os.path.abspath(__file__))

# 組合出正確的 CSV 檔案路徑
file_path = os.path.join(base_dir, '區域人口資料.csv')

# 1. 讀取資料 (使用絕對路徑)
df = pd.read_csv(file_path, skiprows=1)

df.rename(columns={'區 域 別': '區域'}, inplace=True)
df['總平均'] = df['總計']

under_30_cols = [
    '合計_0~4歲', '合計_5~9歲', '合計_10~14歲', 
    '合計_15~19歲', '合計_20~24歲', '合計_25~29歲'
]
df['未滿30歲'] = df[under_30_cols].sum(axis=1)

df['30～34歲'] = df['合計_30~34歲']
df['35～39歲'] = df['合計_35~39歲']
df['40～44歲'] = df['合計_40~44歲']
df['45～54歲'] = df['合計_45~49歲'] + df['合計_50~54歲']
df['55～64歲'] = df['合計_55~59歲'] + df['合計_60~64歲']

over_65_cols = [
    '合計_65~69歲', '合計_70~74歲', '合計_75~79歲', 
    '合計_80~84歲', '合計_85~89歲', '合計_90~94歲', 
    '合計_95~99歲', '100歲以上'
]
df['65歲及以上'] = df[over_65_cols].sum(axis=1)

output_columns = [
    '區域', '總平均', '未滿30歲', '30～34歲', '35～39歲', 
    '40～44歲', '45～54歲', '55～64歲', '65歲及以上'
]
df_clean = df[output_columns]

# 4. 輸出成新的 CSV 檔案
# 使用 utf-8-sig 確保未來無論用 Mac 還是 Windows 的 Excel 打開都不會變成亂碼
df_clean.to_csv('清洗後_區域人口資料.csv', index=False, encoding='utf-8-sig')

print("資料清洗完成！已儲存為：清洗後_區域人口資料.csv")