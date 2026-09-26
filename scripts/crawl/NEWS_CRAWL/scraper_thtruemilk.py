import os
import sys
import json
import re
import time
import base64
import datetime
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Reconfigure stdout/stderr to support Vietnamese characters in Windows console output
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Define variables
BRAND = "TH true MILK"
KEYWORDS = [
    "TH true MILK",
    "TH true MILK marketing",
    "TH true MILK quảng cáo",
    "TH true MILK chiến dịch",
    "sữa TH",
    "TH true MILK doanh thu"
]
OUTPUT_FILE = "th_truemilk_news_dataset.csv"

# Request Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive"
}

def fetch_decoded_batch_execute(id):
    """
    Fetch decoded URL using Google's batch execute service.
    """
    url = f"https://news.google.com/articles/{id}"
    headers = {
        "User-Agent": HEADERS["User-Agent"]
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        html = response.text
        sg_match = re.search(r'data-n-a-sg="([^"]+)"', html)
        ts_match = re.search(r'data-n-a-ts="([^"]+)"', html)
        
        if not sg_match or not ts_match:
            return None
            
        signature = sg_match.group(1)
        timestamp = ts_match.group(1)
        
        articles_req = [
            "Fbv4je",
            json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], id, int(timestamp), signature])
        ]
        
        s = json.dumps([[articles_req]])
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Referer": "https://news.google.com/",
            "User-Agent": HEADERS["User-Agent"]
        }
        
        response = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
            headers=headers,
            data={"f.req": s},
            timeout=15
        )
        
        if response.status_code != 200:
            return None
            
        text = response.text
        header = '[\\"garturlres\\",\\"'
        footer = '\\",'
        if header not in text:
            return None
        start = text.split(header, 1)[1]
        if footer not in start:
            return None
        url = start.split(footer, 1)[0]
        return url
    except Exception as e:
        print(f"Error in fetch_decoded_batch_execute: {e}")
        return None

def decode_google_news_url(source_url):
    """
    Decode Google News redirect URL to the original article URL.
    """
    url = urllib.parse.urlparse(source_url)
    path = url.path.split("/")
    if url.hostname == "news.google.com" and len(path) > 1 and path[-2] in ["articles", "read"]:
        base64_str = path[-1]
        try:
            # Try parsing base64 string directly
            padding = len(base64_str) % 4
            if padding:
                base64_str_padded = base64_str + "=" * (4 - padding)
            else:
                base64_str_padded = base64_str
            decoded_bytes = base64.urlsafe_b64decode(base64_str_padded)
            decoded_str = decoded_bytes.decode("latin1")

            prefix = b"\x08\x13\x22".decode("latin1")
            if decoded_str.startswith(prefix):
                decoded_str = decoded_str[len(prefix) :]

            suffix = b"\xd2\x01\x00".decode("latin1")
            if decoded_str.endswith(suffix):
                decoded_str = decoded_str[: -len(suffix)]

            bytes_array = bytearray(decoded_str, "latin1")
            length = bytes_array[0]
            if length >= 0x80:
                decoded_str = decoded_str[2 : length + 1]
            else:
                decoded_str = decoded_str[1 : length + 1]

            if decoded_str.startswith("AU_yqL"):
                decoded_url = fetch_decoded_batch_execute(base64_str)
                return decoded_url if decoded_url else source_url

            return decoded_str
        except Exception:
            # Fallback to batch execute
            try:
                decoded_url = fetch_decoded_batch_execute(base64_str)
                return decoded_url if decoded_url else source_url
            except Exception:
                return source_url
    else:
        return source_url

def parse_date(pub_date_str):
    """
    Parse pubDate string into YYYY-MM-DD format.
    """
    pub_date_str = pub_date_str.strip()
    for fmt in ('%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z', '%d %b %Y %H:%M:%S %Z', '%Y-%m-%d'):
        try:
            dt = datetime.datetime.strptime(pub_date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    try:
        parts = pub_date_str.split()
        if len(parts) >= 4:
            day = parts[1].zfill(2)
            month_str = parts[2]
            year = parts[3]
            months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                      'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
            month = months.get(month_str[:3], '01')
            return f"{year}-{month}-{day}"
    except Exception:
        pass
    return pub_date_str

def clean_html(html_str):
    """
    Remove HTML tags and get text.
    """
    if not html_str:
        return ""
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        return soup.get_text().strip()
    except Exception:
        return html_str

def clean_title(title, source_name):
    """
    Clean title by removing the source suffix.
    """
    title = title.strip()
    if not title:
        return ""
    if ' - ' in title:
        parts = title.rsplit(' - ', 1)
        if source_name and (source_name.lower() in parts[1].lower() or parts[1].lower() in source_name.lower()):
            return parts[0].strip()
    return title

def main():
    print(f"Starting Scraper for {BRAND}...")
    all_raw_articles = {}
    
    # 1. Fetch from Google News RSS for each keyword
    for idx, keyword in enumerate(KEYWORDS):
        print(f"[{idx+1}/{len(KEYWORDS)}] Searching keyword: '{keyword}'...")
        query_encoded = urllib.parse.quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={query_encoded}&hl=vi&gl=VN&ceid=VN:vi"
        
        try:
            response = requests.get(rss_url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"   Failed to fetch RSS feed (Status code: {response.status_code})")
                continue
                
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            print(f"   Found {len(items)} raw RSS items.")
            
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                source_elem = item.find('source')
                source_name = source_elem.text if source_elem is not None else ""
                
                if not link:
                    continue
                    
                if link not in all_raw_articles:
                    all_raw_articles[link] = {
                        'raw_url': link,
                        'title': title,
                        'pub_date': pub_date,
                        'description': description,
                        'source_name': source_name,
                        'keywords': {keyword}
                    }
                else:
                    all_raw_articles[link]['keywords'].add(keyword)
                    
        except Exception as e:
            print(f"   Error searching keyword '{keyword}': {e}")
            
        time.sleep(1.0)
        
    print(f"\nTotal unique raw articles collected across all keywords: {len(all_raw_articles)}")
    
    # 2. Decode URLs and process articles in parallel
    processed_articles = []
    raw_articles_list = list(all_raw_articles.values())
    total_articles = len(raw_articles_list)
    
    def process_article(art, index):
        link = art['raw_url']
        print(f"[{index+1}/{total_articles}] Decoding URL: {link[:50]}...")
        try:
            decoded_url = decode_google_news_url(link)
        except Exception:
            decoded_url = link
            
        try:
            parsed_domain = urllib.parse.urlparse(decoded_url).netloc
            if parsed_domain.startswith("www."):
                parsed_domain = parsed_domain[4:]
        except Exception:
            parsed_domain = ""
            
        snippet = clean_html(art['description'])
        source_name = art['source_name']
        if not source_name and ' - ' in art['title']:
            source_name = art['title'].rsplit(' - ', 1)[1].strip()
            
        clean_art_title = clean_title(art['title'], source_name)
        published_date = parse_date(art['pub_date'])
        keyword_matched = ", ".join(sorted(list(art['keywords'])))
        
        title_lower = clean_art_title.lower()
        snippet_lower = snippet.lower()
        targets = ["th true milk", "th truemilk", "sữa th"]
        
        if any(target in title_lower or target in snippet_lower for target in targets):
            return {
                'title': clean_art_title,
                'published_date': published_date,
                'source_name': source_name,
                'source_domain': parsed_domain,
                'url': decoded_url,
                'snippet': snippet,
                'brand': BRAND,
                'keyword_matched': keyword_matched
            }
        return None

    # Using 4 workers is a good balance between speed and rate limiting
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_article, art, idx): art for idx, art in enumerate(raw_articles_list)}
        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    processed_articles.append(res)
            except Exception as e:
                print(f"Error processing article: {e}")
        
    print(f"\nFiltered and collected {len(processed_articles)} articles matching TH true MILK.")
    
    # 3. Export to CSV (UTF-8-sig for Excel compatibility)
    df = pd.DataFrame(processed_articles)
    if not df.empty:
        columns_order = ['title', 'published_date', 'source_name', 'source_domain', 'url', 'snippet', 'brand', 'keyword_matched']
        df = df[columns_order]
        
        os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_FILE)) if os.path.dirname(OUTPUT_FILE) else '.', exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(df)} records to '{OUTPUT_FILE}'.")
    else:
        print("No articles found matching the filter rules.")

if __name__ == "__main__":
    main()
