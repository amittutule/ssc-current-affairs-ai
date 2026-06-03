import feedparser
import requests
from bs4 import BeautifulSoup

RSS_FEEDS = [
    "https://indianexpress.com/section/india/feed/",
    "https://www.thehindu.com/news/national/feeder/default.rss"
]

def fetch_latest_news(max_articles=5):
    """
    Fetches the latest news from RSS feeds and extracts text content.
    """
    news_items = []
    
    for feed_url in RSS_FEEDS:
        try:
            # Bypass simple bot blockers
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
            res = requests.get(feed_url, headers=headers, timeout=10)
            parsed_feed = feedparser.parse(res.content)
            
            for entry in parsed_feed.entries[:max_articles]:
                # Basic info
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # The summary from RSS might have HTML or be truncated
                summary_html = entry.get('summary', '')
                
                # Optionally scrape the full article page if summary is too short
                # For simplicity and speed in this demo, we'll just clean the RSS summary. 
                # In a real heavy app, we'd do a requests.get(link) and BeautifulSoup on the body.
                soup = BeautifulSoup(summary_html, "html.parser")
                clean_text = soup.get_text(separator=" ", strip=True)
                
                # If the snippet is too small, let's try to get the original page text
                if len(clean_text) < 150:
                    try:
                        res2 = requests.get(link, headers=headers, timeout=5)
                        page_soup = BeautifulSoup(res2.text, "html.parser")
                        # Find all paragraph tags
                        paragraphs = page_soup.find_all("p")
                        full_text = " ".join([p.get_text() for p in paragraphs])
                        clean_text = full_text if len(full_text) > 150 else clean_text
                    except Exception as e:
                        print(f"Failed to fetch full article for {link}: {e}")

                if clean_text:
                    news_items.append({
                        "title": title,
                        "url": link,
                        "content": clean_text
                    })
        except Exception as e:
            print(f"Failed fetching feed {feed_url}: {e}")
                
    return news_items
