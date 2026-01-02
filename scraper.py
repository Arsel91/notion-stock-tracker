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
        # PSX uses this specific endpoint for company data
        url = f"https://dps.psx.com.pk/ajax/getCompanyInfo/{ticker.upper()}"
        
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 'current' is the field for the latest price in the PSX API response
        price = data.get("current")
        
        if price:
            return float(price)
        else:
            print(f"Price not found in PSX data for {ticker}")
            return None
            
    except Exception as e:
        print(f"Error fetching {ticker} from PSX: {e}")
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
    res = requests.patch(url, headers=headers, json=data)
    return res.status_code == 200

def main():
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Missing Credentials!")
        return

    # Step 1: Query Notion Database
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    
    if res.status_code != 200:
        print(f"Notion Connection Error: {res.text}")
        return

    rows = res.json().get("results", [])
    print(f"Updating {len(rows)} stocks...")

    for row in rows:
        page_id = row["id"]
        
        # Get Ticker from column
        try:
            ticker = row["properties"]["Ticker"]["rich_text"][0]["text"]["content"]
            ticker = ticker.upper().strip()
        except (KeyError, IndexError):
            continue
            
        print(f"Fetching {ticker}...")
        price = get_psx_price(ticker)
        
        if price:
            if update_notion(page_id, price):
                print(f"SUCCESS: {ticker} -> {price}")
            else:
                print(f"FAILED to update Notion for {ticker}")
        
        # 1-second delay to be polite to servers
        time.sleep(1)

if __name__ == "__main__":
    main()
