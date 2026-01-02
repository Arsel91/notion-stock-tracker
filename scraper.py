import requests
from datetime import datetime
import os
import time

# 1. Configuration - Set these in GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_psx_price(ticker):
    """
    Fetches the current stock price from PSX Data Portal API.
    """
    try:
        # The PSX Data Portal uses this endpoint for company info
        url = f"https://dps.psx.com.pk/ajax/getCompanyInfo/{ticker.upper()}"
        
        # We use a standard User-Agent to ensure the request is accepted
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }, timeout=15)
        
        # Check if the page exists or if we are blocked
        if response.status_code != 200:
            print(f"Error: Received status {response.status_code} for {ticker}")
            return None
        
        data = response.json()
        
        # The price is stored in the 'current' key of the JSON response
        price = data.get("current")
        
        if price:
            return float(price)
        else:
            print(f"Price data missing in PSX response for {ticker}")
            return None
            
    except Exception as e:
        print(f"Connection error for {ticker}: {e}")
        return None

def update_notion(page_id, price):
    """Updates the Notion page with the latest price and current timestamp."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Price": {"number": price},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    res = requests.patch(url, headers=headers, json=data)
    return res.status_code

def main():
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: Notion credentials not found in environment.")
        return

    # Fetch rows from Notion
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    
    if res.status_code != 200:
        print(f"Failed to reach Notion: {res.text}")
        return

    results = res.json().get("results", [])
    print(f"Found {len(results)} stocks in Notion database. Starting update...")

    for page in results:
        page_id = page["id"]
        
        # Extract Ticker from the database
        try:
            ticker_data = page["properties"]["Ticker"]["rich_text"]
            if not ticker_data:
                continue
            ticker = ticker_data[0]["text"]["content"].upper().strip()
        except (KeyError, IndexError):
            continue
            
        print(f"Fetching {ticker} from PSX...")
        price = get_psx_price(ticker)
        
        if price:
            status = update_notion(page_id, price)
            if status == 200:
                print(f"SUCCESS: {ticker} updated to {price}")
            else:
                print(f"FAILED: Notion update error {status}")
        
        # Pause to avoid triggering security blocks
        time.sleep(2)

if __name__ == "__main__":
    main()
