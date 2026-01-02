import requests
from datetime import datetime
import os
import time

# 1. Configuration - Set in GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_psx_price(ticker):
    """
    Fetches the current stock price directly from PSX Data Portal.
    """
    try:
        # Use the PSX data portal company info endpoint
        url = f"https://dps.psx.com.pk/ajax/getCompanyInfo/{ticker.upper()}"
        
        # A standard header is used to ensure the request is accepted
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }, timeout=15)
        
        if response.status_code != 200:
            print(f"Failed to fetch {ticker}: {response.status_code}")
            return None
            
        data = response.json()
        
        # 'current' represents the latest trading price in the response
        price = data.get("current")
        
        if price is not None:
            return float(price)
        else:
            print(f"Price field missing for {ticker}")
            return None
            
    except Exception as e:
        print(f"Error connecting to PSX for {ticker}: {e}")
        return None

def update_notion(page_id, price):
    """Updates the Price and Last Updated columns in Notion."""
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
        print("Missing Notion credentials.")
        return

    # Query the database for existing stocks
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    
    if res.status_code != 200:
        print(f"Notion Connection Error: {res.text}")
        return

    rows = res.json().get("results", [])
    print(f"Starting update for {len(rows)} stocks...")

    for row in rows:
        page_id = row["id"]
        
        # Extract the Ticker symbol from the database
        try:
            ticker_rich_text = row["properties"]["Ticker"]["rich_text"]
            if not ticker_rich_text:
                continue
            ticker = ticker_rich_text[0]["text"]["content"].upper().strip()
        except (KeyError, IndexError):
            continue
            
        print(f"Updating {ticker}...")
        price = get_psx_price(ticker)
        
        if price is not None:
            if update_notion(page_id, price):
                print(f"Successfully updated {ticker} to {price}")
            else:
                print(f"Failed to update Notion database for {ticker}")
        
        # Small delay to prevent hitting rate limits
        time.sleep(2)

if __name__ == "__main__":
    main()
