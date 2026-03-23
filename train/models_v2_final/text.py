import pandas as pd

# 載入實價登錄資料 (訓練集的標籤)
real_df = pd.read_csv('maxfinal_taipei_real_price_.csv')

# 篩選大安區、且坪數在 40-55 坪之間的大樓物件
daan_similar = real_df[
    (real_df['district'] == '大安區') & 
    (real_df['building_area'] >= 40) & 
    (real_df['building_area'] <= 55) &
    (real_df['type_building'] == 1)
]

print("大安區同規模物件的實價登錄統計：")
print(daan_similar['unit_price'].describe())