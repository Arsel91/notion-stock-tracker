import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import time

# 1. Configuration - Fetched from GitHub Secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

# Notion API Headers
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_stock_price(ticker):
    """
    Scrapes the current stock price from Sarmaaya.pk
    """
    try:
        url = f"https://sarmaaya.pk/psx/company/{ticker}"
        # User-Agent header prevents the website from blocking the script
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sarmaaya stores the price in a span with ID 'quote_price'
        price_tag = soup.find("span", id="quote_price")
        
        if price_tag:
            # Clean string like "1,250.50" to float 1250.5
            price_str = price_tag.text.replace(",", "").strip()
            return float(price_str)
        else:
            print(f"Could not find price tag for {ticker}")
            return None
            
    except Exception as e:
        print(f"Error scraping {ticker}: {e}")
        return None

def update_notion(page_id, price):
    """
    Updates the Price and Last Updated columns in Notion
    """
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Price": {
                "number": price
            },
            "Last Updated": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            }
        }
    }
    res = requests.patch(url, headers=headers, json=data)
    return res.status_code == 200

def main():
    if not NOTION_TOKEN or not DATABASE_ID:
        print("Error: NOTION_TOKEN or DATABASE_ID not found in environment variables.")
        return

    # Step 1: Query the database to get all rows
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(query_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to connect to Notion. Error: {response.text}")
        return

    data = response.json()
    pages = data.get("results", [])

    if not pages:
        print("No rows found in the database. Make sure you have added stocks and filled the 'Ticker' column.")
        return

    print(f"Found {len(pages)} stocks. Starting update...")

    for page in pages:
        page_id = page["id"]
        props = page["properties"]
        
        # Extract Ticker from the "Ticker" column
        ticker_data = props.get("Ticker", {}).get("rich_text", [])
        if not ticker_data:
            continue
            
        ticker = ticker_data[0]["text"]["content"].upper().strip()
        
        # Step 2: Get the price
        current_price = get_stock_price(ticker)
        
        if current_price is not None:
            # Step 3: Update Notion
            success = update_notion(page_id, current_price)
            if success:
                print(f"Successfully updated {ticker}: {current_price} PKR")
            else:
                print(f"Failed to update Notion for {ticker}")
        
        # Small delay to avoid hitting Sarmaaya or Notion rate limits
        time.sleep(1)

if __name__ == "__main__":
    main()
