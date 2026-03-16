# tpe-real-estate-ai
一條龍專案-房地產市場分析與價格預測系統

資料來源：
1. 內政部網站：https://lvr.land.moi.gov.tw/　
2. 永慶房屋：https://evertrust.yungching.com.tw/
3. 信義房屋：https://www.sinyi.com.tw/tradeinfo/list/Taipei-city/110-zip/6month-dealtime/datatime-desc/
4. 住商不動產：https://www.hbhousing.com.tw/

KPI：
每人資料筆數 ≥ 3000 筆（或影片 ≥ 500 支）
至少 4 個資料來源
至少 1 個分群模型 + 1 個預測模型
至少 3 支 API（可正常回傳 JSON）


工作目標：
1. 資料抓取
• 針對 台北市共 12 區 的各個檔案網站進行 1 年份 的資料抓取。
2. 資料清洗與規格化
• 必要欄位： 區域名稱、成交價/售價、總價格、每坪價格、坪數、屋齡、房屋規格、住宅類型、樓層。
• 儲存要求： 統一依照 EToday 方式 存入 CSV。
• 備份： 各自清洗完成後，請先存放在個人 USB 或 雲端空間 備份。


