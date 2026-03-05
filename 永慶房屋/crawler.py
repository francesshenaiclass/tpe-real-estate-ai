import requests
from bs4 import BeautifulSoup

def get_news_data(pages=3):
    url_base = "https://travel.ettoday.net/category/%E6%AD%90%E6%B4%B2%E6%97%85%E9%81%8A/?&page="
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    for page in range(pages):
        page_url = f"{url_base}{page + 1}"
        response = requests.get(page_url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        result = soup.find_all("h3", attrs={"itemprop": "headline"})
        
        for obj in result:
            title = obj.text.strip()
            a_tag = obj.find("a")
            if a_tag:
                link = a_tag['href']
                res_detail = requests.get(link, headers=headers, verify=False)
                soup_detail = BeautifulSoup(res_detail.text, "html.parser")
                story = soup_detail.find("div", class_="story")
                
                if story:
                    paragraphs = story.find_all("p")
                    full_content = "\n".join([
                        p.text.strip() for p in paragraphs 
                        if p.text.strip() and not p.text.strip().startswith(("▲", "►"))])
                    yield {"title": title, "content": full_content}