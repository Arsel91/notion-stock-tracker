import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Configuration (Set these in GitHub Secrets)
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
    "User-Agent": "Mozilla/5.0"
}

def get_stock_price(ticker):
    """Scrapes the current price from Sarmaaya.pk"""
    url = f"https://sarmaaya.pk/psx/company/{ticker}"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Locate the price element (usually inside a specific ID or class)
    # Note: Inspect Sarmaaya's HTML; as of now, the price is often in id="quote_price"
    price_tag = soup.find("span", id="quote_price")
    if price_tag:
        return float(price_tag.text.replace(",", ""))
    return None

def update_notion(page_id, price):
    """Updates the Notion page with the new price and date"""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Price": {"number": price},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    requests.patch(url, headers=headers, json=data)

def main():
    # 1. Fetch all rows from Notion
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    rows = res.json().get("results", [])

    for row in rows:
        ticker = row["properties"]["Ticker"]["rich_text"][0]["text"]["content"]
        page_id = row["id"]
        
        print(f"Updating {ticker}...")
        current_price = get_stock_price(ticker)
        
        if current_price:
            update_notion(page_id, current_price)
            print(f"Success: {ticker} updated to {current_price}")

if __name__ == "__main__":
    main()
