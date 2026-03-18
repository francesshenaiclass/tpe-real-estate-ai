import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os


# ─────────────────────────────────────────────
# 設定區：請依實際環境修改
# ─────────────────────────────────────────────
load_dotenv()

CSV_PATH    = os.getenv("CSV_PATH", "final_taipei_real_price.csv")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_NAME     = os.getenv("DB_NAME", "db_realestate")
TABLE_NAME  = os.getenv("TABLE_NAME", "house_prices_taipei")
BATCH_SIZE  = int(os.getenv("BATCH_SIZE", 500))
# ─────────────────────────────────────────────

COLUMN_MAPPING = {
    '行政區': 'district',
    '緯度': 'latitude',
    '經度': 'longitude',
    '行政區_中山區': 'dist_zhongshan',
    '行政區_中正區': 'dist_zhongzheng',
    '行政區_信義區': 'dist_xinyi',
    '行政區_內湖區': 'dist_neihu',
    '行政區_北投區': 'dist_beitou',
    '行政區_南港區': 'dist_nangang',
    '行政區_士林區': 'dist_shilin',
    '行政區_大同區': 'dist_datong',
    '行政區_大安區': 'dist_daan',
    '行政區_文山區': 'dist_wenshan',
    '行政區_松山區': 'dist_songshan',
    '行政區_萬華區': 'dist_wanhua',
    '建坪': 'building_area',
    '地坪': 'land_area',
    '房屋總價': 'total_price',
    '單價': 'unit_price',
    '是否有車位': 'has_parking',
    '房': 'rooms',
    '廳': 'halls',
    '衛': 'bathrooms',
    '房屋類型_公寓': 'type_apartment',
    '房屋類型_大樓': 'type_building',
    '房屋類型_華廈': 'type_mansion',
    '房屋類型_透天': 'type_house',
    '成交年月': 'transaction_date',
}

ORDERED_COLS = [
    '行政區', '緯度', '經度',
    '行政區_中山區', '行政區_中正區', '行政區_信義區', '行政區_內湖區',
    '行政區_北投區', '行政區_南港區', '行政區_士林區', '行政區_大同區',
    '行政區_大安區', '行政區_文山區', '行政區_松山區', '行政區_萬華區',
    '建坪', '地坪', '房屋總價', '單價',
    '是否有車位',
    '房', '廳', '衛',
    '房屋類型_公寓', '房屋類型_大樓', '房屋類型_華廈', '房屋類型_透天',
    '成交年月',
]

DISTRICT_MAP = {
    '行政區_中山區': '中山區', '行政區_中正區': '中正區', '行政區_信義區': '信義區',
    '行政區_內湖區': '內湖區', '行政區_北投區': '北投區', '行政區_南港區': '南港區',
    '行政區_士林區': '士林區', '行政區_大同區': '大同區', '行政區_大安區': '大安區',
    '行政區_文山區': '文山區', '行政區_松山區': '松山區', '行政區_萬華區': '萬華區',
}

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS `{TABLE_NAME}` (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  district          VARCHAR(20)   NOT NULL COMMENT '行政區',
  latitude          DOUBLE        NOT NULL COMMENT '緯度',
  longitude         DOUBLE        NOT NULL COMMENT '經度',
  dist_zhongshan    TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_中山區',
  dist_zhongzheng   TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_中正區',
  dist_xinyi        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_信義區',
  dist_neihu        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_內湖區',
  dist_beitou       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_北投區',
  dist_nangang      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_南港區',
  dist_shilin       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_士林區',
  dist_datong       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_大同區',
  dist_daan         TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_大安區',
  dist_wenshan      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_文山區',
  dist_songshan     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_松山區',
  dist_wanhua       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '行政區_萬華區',
  building_area     DOUBLE        NOT NULL COMMENT '建坪',
  land_area         DOUBLE        NOT NULL COMMENT '地坪',
  total_price       DOUBLE        NOT NULL COMMENT '房屋總價',
  unit_price        DOUBLE        NOT NULL COMMENT '單價',
  has_parking       TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '是否有車位',
  rooms             SMALLINT      NOT NULL DEFAULT 0 COMMENT '房',
  halls             SMALLINT      NOT NULL DEFAULT 0 COMMENT '廳',
  bathrooms         SMALLINT      NOT NULL DEFAULT 0 COMMENT '衛',
  type_apartment    TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '房屋類型_公寓',
  type_building     TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '房屋類型_大樓',
  type_mansion      TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '房屋類型_華廈',
  type_house        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '房屋類型_透天',
  transaction_date  INT           NOT NULL COMMENT '成交年月(民國年月, e.g. 11502)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def load_and_transform(csv_path: str) -> pd.DataFrame:
    """讀取 CSV 並進行欄位轉換。"""
    print(f"[1/3] 讀取 CSV：{csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"      原始資料：{df.shape[0]} 筆，{df.shape[1]} 欄")

    # 還原行政區 one-hot → 文字
    district_cols = list(DISTRICT_MAP.keys())
    df['行政區'] = df[district_cols].idxmax(axis=1).map(DISTRICT_MAP)

    # 重排欄位順序 + 重命名
    df = df[ORDERED_COLS].rename(columns=COLUMN_MAPPING)
    print(f"      轉換後欄位（共 {len(df.columns)} 欄）：{df.columns.tolist()}")
    return df


def get_connection(database: str = None):
    """建立 MySQL 連線。"""
    cfg = dict(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset="utf8mb4",
    )
    if database:
        cfg["database"] = database
    return mysql.connector.connect(**cfg)


def setup_database(cursor) -> None:
    """建立資料庫與資料表（若不存在）。"""
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute(f"USE `{DB_NAME}`")
    cursor.execute(f"DROP TABLE IF EXISTS `{TABLE_NAME}`")
    cursor.execute(CREATE_TABLE_SQL)
    print(f"[2/3] 資料庫 `{DB_NAME}` 與資料表 `{TABLE_NAME}` 準備完成")


def write_to_mysql(df: pd.DataFrame) -> None:
    """批次寫入 MySQL。"""
    print(f"[3/3] 寫入 MySQL，共 {len(df)} 筆（每批 {BATCH_SIZE} 筆）...")

    cols = df.columns.tolist()
    placeholders = ", ".join(["%s"] * len(cols))
    col_names = ", ".join([f"`{c}`" for c in cols])
    insert_sql = (
        f"INSERT INTO `{TABLE_NAME}` ({col_names}) VALUES ({placeholders})"
    )

    try:
        # 建立資料庫與資料表
        conn = get_connection()
        cursor = conn.cursor()
        setup_database(cursor)
        conn.commit()
        cursor.close()
        conn.close()

        # 寫入資料
        conn = get_connection(database=DB_NAME)
        cursor = conn.cursor()

        total = len(df)
        for start in range(0, total, BATCH_SIZE):
            batch = df.iloc[start:start + BATCH_SIZE]
            rows = [
                tuple(None if pd.isna(v) else v for v in row)
                for row in batch.itertuples(index=False, name=None)
            ]
            cursor.executemany(insert_sql, rows)
            conn.commit()
            written = min(start + BATCH_SIZE, total)
            print(f"      已寫入：{written} / {total}")

        cursor.close()
        conn.close()
        print(f"✅ 完成！資料已寫入 `{DB_NAME}`.`{TABLE_NAME}`")

    except Error as e:
        print(f"❌ MySQL 錯誤：{e}")
        raise


def main():
    df = load_and_transform(CSV_PATH)
    write_to_mysql(df)


if __name__ == "__main__":
    main()