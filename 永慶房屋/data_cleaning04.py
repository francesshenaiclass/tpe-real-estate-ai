import pandas as pd
import os

# 🌟 新增 GPS 定位：抓取這個 data_cleaning02.py 所在的「絕對路徑」
base_dir = os.path.dirname(os.path.abspath(__file__))

# 組合出正確的 CSV 檔案路徑
file_path = os.path.join(base_dir, '臺北捷運車站出入口座標.csv')

df = pd.read_csv(file_path, skiprows=1)

doutput_columns = [
    '出入口名稱','經度','緯度'
]
df_clean = df[doutput_columns]
# 4. 輸出成新的 CSV 檔案
# 使用 utf-8-sig 確保未來無論用 Mac 還是 Windows 的 Excel 打開都不會變成亂碼
df_clean.to_csv('清洗後_臺北捷運車站出入口座標.csv', index=False, encoding='utf-8-sig')

print("資料清洗完成！已儲存為：清洗後_臺北捷運車站出入口座標.csv")