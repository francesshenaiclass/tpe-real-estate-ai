import pandas as pd
import glob
import os
import numpy as np

print("🛠️ 開始讀取並合併 12 區資料...")

# 1. 讀取並合併所有 CSV (抓取 housing_output 資料夾內的所有檔案)
base_dir = os.path.dirname(os.path.abspath(__file__))
folder_path = os.path.join(base_dir, "housing_output")
all_files = glob.glob(os.path.join(folder_path, "*.csv"))

if not all_files:
    print("⚠️ 找不到任何 CSV 檔案，請確認 housing_output 資料夾內是否有資料！")
    exit()

df_list = [pd.read_csv(f) for f in all_files]
df = pd.concat(df_list, ignore_index=True)

print("🧹 開始進行深度資料清洗與機器學習格式轉換...")

# ==========================================
# 0. 空值標準化與「地址路段過濾」
# ==========================================
# 將各種代表「沒有資料」的幽靈字串全部統一為 np.nan
null_patterns = ['無資料', '--樓', '--房(室)--廳--衛', '--年', '--', '']
df.replace(null_patterns, np.nan, inplace=True)

# 🛑 剔除條件 1：地址只有行政區沒有路段，直接移除
# 我們用一個條件遮罩 (Mask) 來「偷偷檢查」，扣掉「台北市+行政區」後還有沒有路名
has_road = df.apply(lambda row: str(row['地址']).replace(f"台北市{row['區域']}", "").strip() != "" if pd.notna(row['地址']) else False, axis=1)

# 只保留真正有路名的資料
df = df[has_road].copy()

# 🌟 滿足你的需求：完整保留「台北市＋區域＋路段」！
# 因為原本的地址就已經是最完整的格式了，我們直接把它無損複製給「路段」欄位
df['路段'] = df['地址'].astype(str)

# ==========================================
# 1. 缺失值數量容忍度過濾 (超過 3 個空缺即拋棄)
# ==========================================
# 🛑 剔除條件 2：這筆房子只要原始資料超過 3 個欄位是空的，立刻踢掉！
df = df[df.isna().sum(axis=1) <= 3].copy()

# ==========================================
# 2. 數值與特徵抽取 (對應目標 Excel 格式)
# ==========================================
# 價格轉萬元 (拿掉萬字與逗號，原先數字已是萬為單位)
df['房屋總價(萬)'] = df['價格'].astype(str).str.replace(' 萬', '', regex=False)\
                                        .str.replace(r' \(含車位價\)', '', regex=True)\
                                        .str.replace(',', '', regex=False)
df['房屋總價(萬)'] = pd.to_numeric(df['房屋總價(萬)'], errors='coerce')

# 坪數、屋齡、車位抽數字
df['建坪'] = df['總坪數'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
df['屋齡'] = df['屋齡'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
df['車位'] = df['車位'].astype(str).str.extract(r'(\d+)').astype(float)

# 格局拆解 (房, 廳, 衛, 室)
df['房'] = df['規格'].str.extract(r'(\d+)房').astype(float)
df['廳'] = df['規格'].str.extract(r'(\d+)廳').astype(float)
df['衛'] = df['規格'].str.extract(r'(\d+)衛').astype(float)
df['室'] = df['規格'].str.extract(r'(\d+)室').astype(float)

# 是否有加蓋 (布林值轉 0或1)
df['有加蓋'] = df['規格'].str.contains('加蓋', na=False).astype(int)

# 樓層拆解與跨樓層計算
floor_range = df['樓層'].str.extract(r'(.*)/')[0].str.replace('B', '-', regex=False)
df['起始樓層'] = floor_range.str.split('~').str[0].astype(float)
df['最高樓層'] = floor_range.str.split('~').str[-1].astype(float)
df['總樓層'] = df['樓層'].str.extract(r'/(\d+)樓').astype(float)

# 涵蓋層數計算：如果跨越地面層 (例如 B1~2 樓)，因為沒有 0 樓，需要扣除 1
covered = df['最高樓層'] - df['起始樓層'] + 1
crossed_zero = (df['最高樓層'] > 0) & (df['起始樓層'] < 0)
df['物件涵蓋層數'] = np.where(crossed_zero, covered - 1, covered)

# ==========================================
# 3. 填補 3 個以下的空缺值 (使用各區域中位數)
# ==========================================
numeric_cols = [
    '房屋總價(萬)', '建坪', '屋齡', '車位', 
    '房', '廳', '衛', '室', 
    '起始樓層', '最高樓層', '總樓層', '物件涵蓋層數'
]

# 按照區域分群，填補該區域的欄位中位數
for col in numeric_cols:
    df[col] = df.groupby('區域')[col].transform(lambda x: x.fillna(x.median()))

# 如果這整個區域都沒人填寫該欄位 (中位數仍是 NaN)，則補 0 (通常發生在「室」或「車位」)
fill_zero_cols = ['車位', '房', '廳', '衛', '室']
for col in fill_zero_cols:
    df[col] = df[col].fillna(0)

# 將不該有小數點的欄位四捨五入並轉回整數型態 (Int64 可以優雅包容可能遺漏的 NaN)
int_cols = ['車位', '房', '廳', '衛', '室', '起始樓層', '最高樓層', '總樓層', '物件涵蓋層數']
for col in int_cols:
    df[col] = df[col].round().astype('Int64')

# ==========================================
# 4. One-Hot Encoding (行政區與房屋類型)
# ==========================================
# 產生 12 區的 One-Hot 欄位
districts = ['中山區', '中正區', '信義區', '內湖區', '北投區', '南港區', 
             '士林區', '大同區', '大安區', '文山區', '松山區', '萬華區']
for d in districts:
    df[f'行政區_{d}'] = (df['區域'] == d).astype(int)

# 將永慶的「住宅大樓」、「辦公商業大樓」、「透天厝」正規化名稱，並產生類型 One-Hot 欄位
df['類型'] = df['類型'].str.replace('住宅大樓', '大樓').str.replace('辦公商業大樓', '大樓').str.replace('透天厝', '透天')
types = ['公寓', '大樓', '套房', '華廈', '透天']
for t in types:
    df[f'房屋類型_{t}'] = df['類型'].str.contains(t, na=False).astype(int)

# ==========================================
# 5. 組合最終機器學習專用大表並存檔
# ==========================================
# 完全照著你提供的 Excel 欄位名稱排列 (一字不漏)
clean_columns = [
    '路段',
    '行政區_中山區', '行政區_中正區', '行政區_信義區', '行政區_內湖區', 
    '行政區_北投區', '行政區_南港區', '行政區_士林區', '行政區_大同區', 
    '行政區_大安區', '行政區_文山區', '行政區_松山區', '行政區_萬華區', 
    '屋齡', '建坪', '房屋總價(萬)', '車位', 
    '房', '廳', '衛', '室', '有加蓋', 
    '總樓層', '起始樓層', '最高樓層', '物件涵蓋層數', 
    '房屋類型_公寓', '房屋類型_大樓', '房屋類型_套房', '房屋類型_華廈', '房屋類型_透天'
]

df_clean = df[clean_columns].copy()

# 存檔至獨立資料夾
output_folder = os.path.join(base_dir, "cleaned_data")
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 組合出完整的檔案路徑
output_filename = os.path.join(output_folder, "台北市12區_ML專用格式完成版.csv")

# 存出包含 UTF-8 BOM 格式的 CSV (Excel 打開才不會變亂碼)
df_clean.to_csv(output_filename, index=False, encoding="utf-8-sig")

print(f"✨ 深度清洗與特徵工程完畢！乾淨無瑕的機器學習大表已存放在：\n📂 {output_filename}")