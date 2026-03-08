import pandas as pd
import glob
import os

print("🛠️ 開始讀取並合併 12 區資料...")

# 1. 讀取並合併所有 CSV (抓取 housing_output 資料夾內的所有檔案)
# 🌟 新增 GPS 定位：抓取這個 data_cleaning.py 所在的「絕對路徑」
base_dir = os.path.dirname(os.path.abspath(__file__))

# 🌟 讓程式去正確的地方找 housing_output 資料夾
folder_path = os.path.join(base_dir, "housing_output")
all_files = glob.glob(os.path.join(folder_path, "*.csv"))
df_list = [pd.read_csv(f) for f in all_files]
df = pd.concat(df_list, ignore_index=True)

print("🧹 開始進行深度資料清洗...")

# ==========================================
# 1. 價格與單價處理
# ==========================================
df['價格_元'] = df['價格'].astype(str).str.replace(' 萬', '', regex=False)\
                                    .str.replace(r' \(含車位價\)', '', regex=True)\
                                    .str.replace(',', '', regex=False)
df['價格_元'] = (pd.to_numeric(df['價格_元'], errors='coerce') * 10000).astype(int)

# ==========================================
# 2. 坪數與屋齡擷取 (抽數字)
# ==========================================
df['總坪數_坪'] = df['總坪數'].str.extract(r'(\d+\.?\d*)').astype(float)
df['實際坪數_坪'] = df['實際坪數'].str.extract(r'(\d+\.?\d*)').astype(float)
df['屋齡_年'] = df['屋齡'].str.extract(r'(\d+\.?\d*)').astype(float)

# 計算單價 (總價 / 總坪數)
df['單價_元'] = round(df['價格_元'] / df['總坪數_坪'], 2)

# ==========================================
# 3. 格局與樓層拆解
# ==========================================
# 拆解房、廳、衛
df['房'] = df['規格'].str.extract(r'(\d+)房').astype(float).fillna(0).astype(int)
df['廳'] = df['規格'].str.extract(r'(\d+)廳').astype(float).fillna(0).astype(int)
df['衛'] = df['規格'].str.extract(r'(\d+)衛').astype(float).fillna(0).astype(int)

# 拆解樓層 (處理地下室 B 轉換為負數)
current_floor = df['樓層'].str.extract(r'([B\d]+)/')[0]
df['所在樓層'] = current_floor.str.replace('B', '-', regex=False).astype(float).fillna(0).astype(int)
df['總樓層'] = df['樓層'].str.extract(r'/(\d+)樓').astype(float).fillna(0).astype(int)
# ==========================================
# 🛑 精準防線：空殼與異端值剔除
# ==========================================
# 防線 A：只要這筆資料連「價格」或「總坪數」都抽不出數字，直接踢掉
df = df.dropna(subset=['價格_元', '總坪數_坪'])

# 防線 B：如果一筆資料「沒有所在樓層」且「0房0衛」，它極大機率是一塊地或無效資料，踢掉
invalid_mask = df['所在樓層'].isna() & (df['房'] == 0) & (df['衛'] == 0)
df = df[~invalid_mask]

# ==========================================
# 4. 空值填補
# ==========================================
# 用各區的中位數合理填補缺漏值
df['屋齡_年'] = df.groupby('區域')['屋齡_年'].transform(lambda x: x.fillna(x.median()))
df['所在樓層'] = df.groupby('區域')['所在樓層'].transform(lambda x: x.fillna(x.median()))
df['總樓層'] = df.groupby('區域')['總樓層'].transform(lambda x: x.fillna(x.median()))

# 實際坪數若為空，暫時補 0
df['實際坪數_坪'] = df['實際坪數_坪'].fillna(0)

# ==========================================
# 5. 挑選最終乾淨欄位並存檔到「獨立的新資料夾」
# ==========================================
clean_columns = [
    '區域', '建案名稱', '地址', '類型', '車位', 
    '價格_元', '單價_元', '總坪數_坪', '實際坪數_坪', '屋齡_年', 
    '房', '廳', '衛', '所在樓層', '總樓層'
]

df_clean = df[clean_columns]

# 🌟 幫存檔路徑也加上 GPS 定位！確保它存在專案資料夾裡
output_folder = os.path.join(base_dir, "cleaned_data")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 組合出完整的檔案路徑
output_filename = os.path.join(output_folder, "永慶房屋台北市12區清洗資料檔.csv")

# 存出包含 UTF-8 BOM 格式的 CSV (讓 Excel 打開不會亂碼)
df_clean.to_csv(output_filename, index=False, encoding="utf-8-sig")

print(f"✨ 清洗完畢！純淨大表已安全存放在：\n📂 {output_filename}")