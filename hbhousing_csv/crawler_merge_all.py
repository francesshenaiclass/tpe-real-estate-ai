import pandas as pd
import numpy as np
import re
import os
import glob

# 目標行政區列表
DISTRICTS = ['中山區','中正區','信義區','內湖區','北投區','南港區','士林區','大同區','大安區','文山區','松山區','萬華區']

# 住宅類型
HOUSE_TYPES = ['公寓','大樓','套房','華廈','透天']

def parse_layout(layout_str):
    """解析格局字串，回傳 (房, 廳, 衛, 室)"""
    layout_str = str(layout_str).strip()
    房, 廳, 衛, 室 = np.nan, np.nan, np.nan, np.nan
    m_room = re.search(r'(\d+)房\(室\)', layout_str)
    m_hall = re.search(r'(\d+)廳', layout_str)
    m_bath = re.search(r'(\d+)衛', layout_str)
    if m_room:
        房 = int(m_room.group(1))
    if m_hall:
        廳 = int(m_hall.group(1))
    if m_bath:
        衛 = int(m_bath.group(1))
    室 = 房
    return 房, 廳, 衛, 室

def parse_floor(floor_str):
    """
    解析樓層字串，回傳 (有加蓋, 總樓層, 起始樓層, 最高樓層, 物件涵蓋層數)
    格式範例: 3/4樓, 1-2/2樓, B1-2/2樓, 19/19樓(缺失)
    """
    floor_str = str(floor_str).strip()
    有加蓋 = 0
    總樓層 = np.nan
    起始樓層 = np.nan
    最高樓層 = np.nan
    物件涵蓋層數 = np.nan

    # 19/19樓 → 代表缺失值
    if floor_str == '19/19樓':
        return 有加蓋, 總樓層, 起始樓層, 最高樓層, 物件涵蓋層數

    # 解析總樓層（/ 後面）
    total_match = re.search(r'/(\d+)樓', floor_str)
    if total_match:
        總樓層 = int(total_match.group(1))

    # 解析物件起始與最高樓層（/ 前面）
    floor_part = floor_str.split('/')[0] if '/' in floor_str else floor_str

    b_match = re.match(r'B(\d+)-(\d+)', floor_part)
    range_match = re.match(r'(\d+)-(\d+)', floor_part)
    single_match = re.match(r'B?(\d+)$', floor_part)

    if b_match:
        起始樓層 = -int(b_match.group(1))
        最高樓層 = int(b_match.group(2))
    elif range_match:
        起始樓層 = int(range_match.group(1))
        最高樓層 = int(range_match.group(2))
    elif single_match:
        if floor_part.startswith('B'):
            起始樓層 = -int(single_match.group(1))
        else:
            起始樓層 = int(single_match.group(1))
        最高樓層 = 起始樓層

    # 有加蓋判斷：物件最高樓層 > 建物總樓層
    if not np.isnan(最高樓層) and not np.isnan(總樓層):
        if 最高樓層 > 總樓層:
            有加蓋 = 1
            最高樓層 = 總樓層

    # 物件涵蓋層數
    if not np.isnan(起始樓層) and not np.isnan(最高樓層):
        物件涵蓋層數 = int(最高樓層 - 起始樓層 + 1)

    return 有加蓋, 總樓層, 起始樓層, 最高樓層, 物件涵蓋層數

def parse_area(area_str):
    """解析坪數，如 42坪 → 42.0"""
    m = re.search(r'(\d+\.?\d*)', str(area_str).strip())
    return float(m.group(1)) if m else np.nan

def parse_address(addr_str):
    """從地址拆出行政區與路段"""
    addr_str = str(addr_str).strip()
    for d in DISTRICTS:
        if d in addr_str:
            return d, addr_str.replace(d, '').strip()
    return '', addr_str

def get_house_type(type_str, name_str=''):
    """從類型與物件名稱判斷房屋類型"""
    combined = str(type_str) + str(name_str)
    if '透天' in combined: return '透天'
    if '華廈' in combined: return '華廈'
    if '套房' in combined or '獨立套房' in str(type_str): return '套房'
    if '大樓' in combined: return '大樓'
    if '公寓' in combined: return '公寓'
    if str(type_str).strip() == '住宅': return '大樓'  # 預設
    return ''

def transform_df(df):
    """將原始 DataFrame 轉換為目標欄位格式"""
    results = []
    for _, row in df.iterrows():
        district, road = parse_address(row['地址'])
        房, 廳, 衛, 室 = parse_layout(row['格局'])
        有加蓋, 總樓層, 起始樓層, 最高樓層, 物件涵蓋層數 = parse_floor(row['樓層'])
        house_type = get_house_type(row['類型'], row['物件名稱'])

        record = {'物件名稱': row['物件名稱'], '路段': road}

        # 行政區 one-hot
        for d in DISTRICTS:
            record[f'行政區_{d}'] = 1 if district == d else 0

        record['建坪']       = parse_area(row['坪數'])
        record['車位']       = 1 if '車位' in str(row['類型']) + str(row['物件名稱']) else 0
        record['房']         = 房
        record['廳']         = 廳
        record['衛']         = 衛
        record['室']         = 室
        record['有加蓋']     = 有加蓋
        record['總樓層']     = 總樓層
        record['起始樓層']   = 起始樓層
        record['最高樓層']   = 最高樓層
        record['物件涵蓋層數'] = 物件涵蓋層數

        # 房屋類型 one-hot
        for ht in HOUSE_TYPES:
            record[f'房屋類型_{ht}'] = 1 if house_type == ht else 0

        results.append(record)
    return pd.DataFrame(results)


# ── 主程式：批次處理所有區的 CSV ──────────────────────────────
if __name__ == '__main__':
    INPUT_DIR = "."   # 修改為 CSV 檔案所在目錄

    all_dfs = []
    csv_files = glob.glob(os.path.join(INPUT_DIR, '*區.csv'))

    for path in sorted(csv_files):
        name = os.path.splitext(os.path.basename(path))[0]
        df = pd.read_csv(path, encoding='utf-8-sig')
        result = transform_df(df)
        result.to_csv(f'{name}_轉換.csv', index=False, encoding='utf-8-sig')
        all_dfs.append(result)
        print(f'{name}: {len(df)} 筆 → 轉換完成')

    if all_dfs:
        merged = pd.concat(all_dfs, ignore_index=True)
        merged.to_csv('crawler_merge_all.csv', index=False, encoding='utf-8-sig')
        print(f'\n全區合併: {len(merged)} 筆，已儲存至 crawler_merge_all.csv')
