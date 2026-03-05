import requests
from bs4 import BeautifulSoup
import time
import csv
import re

def restore_csv(title, full_content):
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    file_name = f"{safe_title}.csv"
    with open(file_name, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["文章內文"])
        writer.writerow([full_content])

def get_html_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
    response = requests.get(url, headers=headers)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, "html.parser")
    return soup

def get_article_title(soup):
    article_links = []
    a_tag = soup.select('a.pic')
    if a_tag:
        for tag in a_tag:
            article_url = tag.get('href')
            if article_url:
                article_links.append(article_url)
    else:
        print("找不到指定的標籤")
    return article_links

def scrape_article_detail(article_url):
    article_soup = get_html_content(article_url)
    title_tags = article_soup.select_one('h1.title')
    title = title_tags.text.strip()

    content_tags = article_soup.select('div.story p')

    content_list = []
    for p in content_tags:
        text = p.text.strip()
        if text and "▲" not in text and "►" not in text and "【你可能也想看】"not in text:
            content_list.append(text)
    full_content = "\n".join(content_list)
    print(f"【標題】: {title}")
    print(f"【內文】: {full_content}\n")
    restore_csv(title, full_content)
    save_to_mysql(title, full_content)
    print("-" * 50)

if __name__ == "__main__":
    
    for page in range(1,4):
        print(f"\n" + "="*50)
        print(f"準備開始爬取【第 {page} 頁】的文章列表...")
        print("="*50 + "\n")

        post_codes = f"{}"
        target_url = f"https://www.leju.com.tw/object_list?city_code=A&post_codes={}"
        list_page_soup = get_html_content(target_url)
        all_links = get_article_title(list_page_soup)
    
        if all_links:
                for link in all_links:
                    scrape_article_detail(link)
                    time.sleep(3)