import requests
from datetime import datetime
import os
import time

# Configuration - Set these in GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# Headers for Notion API
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_psx_price(ticker):
    """
    Fetches the current price directly from the official PSX Data Portal.
    """
    try:
        # The PSX Data Portal uses this endpoint for company information
        url = f"https://dps.psx.com.pk/ajax/getCompanyInfo/{ticker.upper()}"
        
        # A realistic user-agent is required to ensure the server accepts the request
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }, timeout=15)
        
        if response.status_code != 200:
            print(f"Error: Received {response.status_code} for {ticker}")
            return None
            
        data = response.json()
        
        # 'current' contains the latest traded price in the PSX API response
        price = data.get("current")
        
        if price is not None:
            return float(price)
        else:
            print(f"Price field missing in PSX data for {ticker}")
            return None
            
    except Exception as e:
        print(f"Connection error for {ticker}: {e}")
        return None

def update_notion(page_id, price):
    """Updates the Notion row with the new price and timestamp."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Price": {"number": price},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    res = requests.patch(url, headers=headers, json=payload)
    return res.status_code == 200

def main():
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Missing Notion credentials in environment variables.")
        return

    # Query the Notion database to find all stock pages
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    
    if res.status_code != 200:
        print(f"Notion API error: {res.text}")
        return

    pages = res.json().get("results", [])
    print(f"Starting update for {len(pages)} stocks...")

    for page in pages:
        page_id = page["id"]
        
        # Extract Ticker from the database column
        try:
            ticker_list = page["properties"]["Ticker"]["rich_text"]
            if not ticker_list:
                continue
            ticker = ticker_list[0]["text"]["content"].upper().strip()
        except (KeyError, IndexError):
            continue
            
        print(f"Updating {ticker}...")
        current_price = get_psx_price(ticker)
        
        if current_price is not None:
            if update_notion(page_id, current_price):
                print(f"SUCCESS: {ticker} updated to {current_price}")
            else:
                print(f"FAILED: Notion update for {ticker} failed.")
        
        # Small delay to prevent rate limiting
        time.sleep(2)

if __name__ == "__main__":
    main()
