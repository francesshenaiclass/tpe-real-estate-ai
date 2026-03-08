import pandas as pd
import glob #用來搜尋符合條件的檔案
import os #用來處理檔案路徑

# 1. 定義資料夾名稱
folder_path = 'result_csv' #定義資料夾路徑，這裡假設所有 CSV 檔都放在 result_csv 資料夾裡。

# 2. 使用 glob 抓取該資料夾下所有的 .csv 檔
# 這會得到類似 ['result_csv/大安區.csv', 'result_csv/士林區.csv', ...] 的列表
files = glob.glob(os.path.join(folder_path, '*.csv'))

df_list = [] #建立一個空的 list，用來存放每個 CSV 讀進來的 DataFrame。

# 3. 跑迴圈讀取
for f in files:
    # 讀取檔案，建議加上 encoding='utf-8-sig' 避免中文亂碼
    temp_df = pd.read_csv(f, encoding='utf-8-sig')
    
    # 【進階技巧】從「檔名」提取行政區名稱，並新增成一欄
    # os.path.basename(f) 會拿到 "大安區.csv"
    # split('.') 會把它切開，拿第 0 個就是 "大安區"
    dist_name = os.path.basename(f).split('.')[0]
    temp_df['行政區'] = dist_name
    
    df_list.append(temp_df)

# 4. 一次性合併
df = pd.concat(df_list, ignore_index=True)
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.colheader_justify", "center")


print(f"✅ 已從 {folder_path} 資料夾合併 {len(files)} 個檔案！")
print(f"📊 目前大表總共有 {len(df)} 筆資料。")

df.to_csv("merged.csv", index=False, encoding="utf-8-sig")