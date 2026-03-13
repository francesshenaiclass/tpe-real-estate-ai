import requests
import os
import json

# 建立 json資料夾
if not os.path.exists("taipei_json"):
    os.makedirs("taipei_json")

api_url = "https://sinyiwebapi.sinyi.com.tw/filterObject.php"

headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://www.sinyi.com.tw',
    'Referer': 'https://www.sinyi.com.tw/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    'code': '0',
    'sat': '730282',
    'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sid': '20260304191613455',
}

# 輸入各縣市資料
with open("cities.json", "r", encoding="utf-8") as f:
    cities = json.load(f)

for city in cities.keys():# 取出每一個縣市
    for district, zipcode in cities[city].items():# 取出每個縣市的行政區及郵遞區號
        file_path = f"taipei_json/{district}.json"
       
        json_data = {
            'machineNo': '',
            'ipAddress': '101.10.246.93',
            'osType': 3,
            'model': 'web',
            'deviceVersion': 'Windows 10',
            'appVersion': '145.0.0.0',
            'deviceType': 3,
            'apType': 3,
            'browser': 1,
            'memberId': '',
            'domain': 'www.sinyi.com.tw',
            'utmSource': '',
            'utmMedium': '',
            'utmCampaign': '',
            'utmCode': '',
            'requestor': 1,
            'utmContent': '',
            'utmTerm': '',
            'sinyiGroup': 1,
            'filter': {
                'exludeSameTrade': False,
                'objectStatus': 0,
                'retType': 2,
                'retRange': [
                    zipcode,
                ],
                'mapType': 1,
                'houselandtype': [
                    'A',
                    'L',
                    'M',
                    'C',
                    'D',
                ],
                'objectType': [
                    1,
                ],
            },
            'page': 1,
            'pageCnt': 1,
            'sort': '0',
            'isReturnTotal': True,
        }

        response = requests.post(api_url, headers=headers, json=json_data)
        result = response.json()
        totalCnt = result["content"]["totalCnt"]

        json_data = {
            'machineNo': '',
            'ipAddress': '101.10.246.93',
            'osType': 3,
            'model': 'web',
            'deviceVersion': 'Windows 10',
            'appVersion': '145.0.0.0',
            'deviceType': 3,
            'apType': 3,
            'browser': 1,
            'memberId': '',
            'domain': 'www.sinyi.com.tw',
            'utmSource': '',
            'utmMedium': '',
            'utmCampaign': '',
            'utmCode': '',
            'requestor': 1,
            'utmContent': '',
            'utmTerm': '',
            'sinyiGroup': 1,
            'filter': {
                'exludeSameTrade': False,
                'objectStatus': 0,
                'retType': 2,
                'retRange': [
                    zipcode,
                ],
                'mapType': 1,
                'houselandtype': [
                    'A',
                    'L',
                    'M',
                    'C',
                    'D',
                ],
                'objectType': [
                    1,
                ],
            },
            'page': 1,
            'pageCnt': totalCnt,
            'sort': '0',
            'isReturnTotal': True,
        }

        response = requests.post(api_url, headers=headers, json=json_data)
        result = response.json()

        # 美化輸出並存檔
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)

            print(f"已儲存至{file_path}")