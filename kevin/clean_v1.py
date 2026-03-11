import pandas as pd
import re

file_path = "house_csv/merged.csv"
df = pd.read_csv(file_path, encoding="utf-8-sig")

# 校正輸出位置
pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.colheader_justify", "center")

# ----------------------------------------------------------------------
# 清洗屋齡
df['屋齡'] = df['屋齡'].str.replace('年', '')
df = df[~df["屋齡"].isin(['預售', '--'])]  # 刪掉屋齡為 '預售' 或 '--' 的列
df["屋齡"] = df["屋齡"].astype(float)

# 清洗格局
def extract_layout(text, unit):  # 定義一個函數來提取格局數字
    pattern = rf'(\d+){unit}'
    match = re.search(pattern, str(text))
    return float(match.group(1)) if match else 0.0

df['房'] = df['格局'].apply(lambda x: extract_layout(x, '房'))
df['廳'] = df['格局'].apply(lambda x: extract_layout(x, '廳'))
df['衛'] = df['格局'].apply(lambda x: extract_layout(x, '衛'))
df['室'] = df['格局'].apply(lambda x: extract_layout(x, '室'))

# ------------------------------------------------------------------

#樓層清洗

def parse_floor_span_v3(floor_str):
    if pd.isna(floor_str) or floor_str == '' or floor_str == 'nan':
        return 0, 0, 0
    
    # 1. 統一清理與標準化分隔符
    # 將「、」統一代換成「,」，方便後續處理不連續樓層
    s = str(floor_str).replace('樓', '').replace('、', ',').strip()
    
    # 定義一個內部函數：處理單個樓層字串（包含 B1 或 -1）轉成整數
    def to_int(p):
        p = p.strip()
        if p.startswith('B'):
            return -int(p[1:])
        if p.startswith('-') and len(p) > 1:
            return -int(p[1:])
        return int(p)

    # 2. 拆分「,」群組 (處理 1, 4-5 這種情況)
    groups = s.split(',')
    all_floors = set() # 使用集合來存儲所有涵蓋的樓層，避免重複

    for group in groups:
        group = group.strip()
        if not group:
            continue
            
        if '-' in group:
            # 處理範圍型，例如 "4-5" 或 "B1-2"
            # 為了避免 B1-2 的負號與間隔號混淆，先做標記替換
            temp = group.replace('-B', '-neg').replace('--', '-neg')
            parts = temp.split('-')
            parts = [p for p in parts if p]
            
            vals = []
            for p in parts:
                if 'neg' in p:
                    vals.append(-int(p.replace('neg', '')))
                else:
                    vals.append(to_int(p))
            
            if len(vals) >= 2:
                low, high = min(vals), max(vals)
                # 將範圍內的每一層都加入集合（建築通常沒有 0 樓）
                for f in range(low, high + 1):
                    if f != 0:
                        all_floors.add(f)
            elif len(vals) == 1:
                all_floors.add(vals[0])
        else:
            # 處理單一樓層型，例如 "1"
            all_floors.add(to_int(group))

    if not all_floors:
        return 0, 0, 0

    # 3. 定義結果
    start_f = min(all_floors)  # 集合中的最小值
    end_f = max(all_floors)    # 集合中的最大值
    span = len(all_floors)     # 集合的大小即為「物件涵蓋層數」
    
    return start_f, end_f, span


# 應用到 DataFrame
df[['起始樓層', '最高樓層', '物件涵蓋層數']] = df['樓層'].apply(
    lambda x: pd.Series(parse_floor_span_v3(x))
)

# 清理房屋類型
# 1. 定義對照表與目標集合
type_map = {
    "A": "公寓",
    "L": "大樓",
    "M": "華廈",
    "C": "套房",
    "D": "透天"
}
# 使用集合 (Set) 來檢查，速度最快
target_codes = {"A", "L", "M", "C", "D"}

def clean_house_type_strict(type_list_str):
    # 解析字串內容，例如把 "['L']" 變成 ["L"]
    # 這裡處理掉引號、空格、中括號
    s = str(type_list_str).strip("[]").replace("'", "").replace(" ", "")
    codes = [c for c in s.split(",") if c]
    
    # 【規則 1】：標籤數量必須剛好等於 1
    if len(codes) != 1:
        return None
    
    # 【規則 2】：這個唯一的標籤必須在我們的目標集合中
    code = codes[0]
    if code in target_codes:
        return type_map[code]
    else:
        # 如果是 ['E'] (店面) 這種雖然只有一個但類別不對的，也回傳 None
        return None

# 2. 執行轉換
df['房屋類型'] = df['房屋類型'].apply(clean_house_type_strict)

# 進行 One-Hot Encoding
df = pd.get_dummies(df, columns=['行政區', '房屋類型'], dtype=int)

# 1. 定義目標欄位順序 (target_columns)
target_columns = [
    '路段', '緯度', '經度', 
    '行政區_中山區', '行政區_中正區', '行政區_信義區', '行政區_內湖區', 
    '行政區_北投區', '行政區_南港區', '行政區_士林區', '行政區_大同區', 
    '行政區_大安區', '行政區_文山區', '行政區_松山區', '行政區_萬華區', 
    '屋齡', '建坪', '房屋總價(萬)', '車位', 
    '房', '廳', '衛', '室', '有加蓋', 
    '總樓層', '起始樓層', '最高樓層', '物件涵蓋層數', 
    '房屋類型_公寓', '房屋類型_大樓', '房屋類型_套房', '房屋類型_華廈', '房屋類型_透天'
]

df_clean_final = df[target_columns].copy()

df_clean_final.to_csv(f"house_csv/clean.csv", index=False, encoding="utf-8-sig")


print(df)
