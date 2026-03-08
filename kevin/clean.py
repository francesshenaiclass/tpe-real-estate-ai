import pandas as pd
import re

file_path = "merged.csv"
df = pd.read_csv(file_path, encoding = "utf-8-sig")

#校正輸出位置
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.colheader_justify", "center")

#----------------------------------------------------------------------
#清洗屋齡
df['屋齡'] = df['屋齡'].str.replace('年', '')
df = df[~df["屋齡"].isin(['預售', '--'])]# 刪掉屋齡為 '預售' 或 '--' 的列
df["屋齡"] = df["屋齡"].astype(float)

#----------------------------------------------------------------------
#清洗房屋類型
df.loc[df['房屋類型'].str[:2] == '大樓', '房屋類型'] = '大樓'
df.loc[df['房屋類型'].str[:2] == '公寓', '房屋類型'] = '公寓'
df.loc[df['房屋類型'].str[:2] == '套房', '房屋類型'] = '套房'
df.loc[df['房屋類型'].str[:2] == '透天', '房屋類型'] = '透天'
df.loc[df['房屋類型'].str[:2] == '華廈', '房屋類型'] = '華廈'
df = df[df['房屋類型'].isin(['大樓', '公寓', '套房', '透天', '華廈'])]

#------------------------------------------------------------------------
#清洗建坪
df['建坪'] = df['建坪'].str.replace('建坪 ', '')
df['建坪'] = df['建坪'].astype(float)
#-----------------------------------------------------------------------
#清洗房屋總價
df['房屋總價(萬)'] = df['房屋總價(萬)'].str.replace(',', '')
df['房屋總價(萬)'] = df['房屋總價(萬)'].astype(float)

#----------------------------------------------------------------------
# 清洗格局
def extract_layout(text, unit): # 定義一個函數來提取格局數字
    pattern = rf'(\d+){unit}'
    match = re.search(pattern, str(text))
    return float(match.group(1)) if match else 0.0

df['房'] = df['格局'].apply(lambda x: extract_layout(x, '房'))
df['廳'] = df['格局'].apply(lambda x: extract_layout(x, '廳'))
df['衛'] = df['格局'].apply(lambda x: extract_layout(x, '衛'))
df['室'] = df['格局'].apply(lambda x: extract_layout(x, '室'))

# 處理「室」或「加蓋」可以增加一個布林特徵
df['有加蓋'] = df['格局'].str.contains('加蓋').astype(int)
#------------------------------------------------------------------

#樓層清洗
df['目前樓層'] = df['樓層'].str.split('/').str[0]
df['總樓層'] = df['樓層'].str.split('/').str[1].str.extract(r'(\d+)').astype(float)
#df['目前樓層'] = df['目前樓層'].str.replace('樓', '')
def parse_floor_span_v2(floor_str):
    if pd.isna(floor_str) or floor_str == '':
        return 0, 0, 0
    
    # 1. 統一清理：去掉「樓」，把「B」或開頭的「-」換成特定的標記 "neg"
    # 這樣可以避免跟中間的分割線 "-" 搞混
    s = str(floor_str).replace('樓', '').strip()
    
    # 處理地下室標記
    if s.startswith('B'):
        s = 'neg' + s[1:]
    elif s.startswith('-'):
        s = 'neg' + s[1:]
    
    # 處理中間可能還有 B 的情況 (例如 1-B1)
    s = s.replace('-B', '-neg')

    # 2. 現在用中間的 "-" 拆分，這時候的 "-" 肯定是分隔符
    parts = s.split('-')
    parts = [p for p in parts if p] # 移除空字串

    vals = []
    for p in parts:
        if 'neg' in p:
            # 轉回負數
            val = -int(p.replace('neg', ''))
        else:
            val = int(p)
        vals.append(val)

    # 3. 定義起始與結束
    if len(vals) == 1:
        start_f = end_f = vals[0]
    else:
        start_f = vals[0]
        end_f = vals[-1]
    
    # 4. 計算總層數 (考慮建築無 0 樓)
    if start_f < 0 and end_f > 0:
        span = end_f - start_f # 例如 B1(-1) 到 1 樓 = 2 層
    else:
        span = abs(end_f - start_f) + 1
        
    return start_f, end_f, span

# 應用到 DataFrame
df[['起始樓層', '最高樓層', '物件涵蓋層數']] = df['目前樓層'].apply(
    lambda x: pd.Series(parse_floor_span_v2(x))
)

# 進行 One-Hot Encoding
df = pd.get_dummies(df, columns=['行政區', '房屋類型'], dtype=int)

# 建立一個「單價」欄位 (萬/坪)
df['單價(萬/坪)'] = df['房屋總價(萬)'] / df['建坪']

# 刪除不需要的文字欄位
cols_to_drop = ['格局', '樓層', '主建物/陽台', '目前樓層']
df_final = df.drop(columns=cols_to_drop)

df_final.to_csv("clean.csv", index=False, encoding="utf-8-sig")
print(df)