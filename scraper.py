import requests
from datetime import datetime
import os
import time

# 1. Configuration - Fetched from GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_psx_price(ticker):
    """
    Fetches the current stock price directly from PSX Data Portal API.
    """
    try:
        # Official PSX Data Portal endpoint for company information
        url = f"https://dps.psx.com.pk/ajax/getCompanyInfo/{ticker.upper()}"
        
        # We use a standard User-Agent to prevent the server from blocking the request
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }, timeout=15)
        
        response.raise_for_status()
        data = response.json()
        
        # 'current' is the field for the latest price in the PSX API response
        price = data.get("current")
        
        if price is not None:
            return float(price)
        else:
            print(f"Price not found in PSX data for {ticker}")
            return None
            
    except Exception as e:
        print(f"Error fetching {ticker} from PSX: {e}")
        return None

def update_notion(page_id, price):
    """Updates the Notion page with the new price and current timestamp."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Price": {"number": price},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    res = requests.patch(url, headers=headers, json=data)
    return res.status_code == 200

def main():
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Missing Credentials! Please check your GitHub Secrets.")
        return

    # Step 1: Query Notion Database
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    
    if res.status_code != 200:
        print(f"Notion Connection Error: {res.text}")
        return

    rows = res.json().get("results", [])
    if not rows:
        print("No stocks found in your Notion database. Check your filters or Ticker column.")
        return

    print(f"Found {len(rows)} stocks. Starting update...")

    for row in rows:
        page_id = row["id"]
        
        # Get Ticker from the database column
        try:
            ticker_list = row["properties"]["Ticker"]["rich_text"]
            if not ticker_list:
                continue
            ticker = ticker_list[0]["text"]["content"].upper().strip()
        except (KeyError, IndexError):
            continue
            
        print(f"Updating {ticker}...")
        price = get_psx_price(ticker)
        
        if price is not None:
            if update_notion(page_id, price):
                print(f"SUCCESS: {ticker} -> {price} PKR")
            else:
                print(f"FAILED to update Notion for {ticker}")
        
        # 2-second delay to avoid triggering rate limits or security blocks
        time.sleep(2)

if __name__ == "__main__":
    main()
