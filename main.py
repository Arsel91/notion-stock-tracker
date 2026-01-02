import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Configuration
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

def get_stock_price(symbol):
    url = f"https://dps.psx.com.pk/company/{symbol}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Finding the price from the PSX Data Portal structure
    price_element = soup.find('div', class_='stats_value')
    if price_element:
        price_text = price_element.text.strip().replace(',', '')
        return float(price_text)
    return None

def update_notion_row(page_id, price):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Price": {"number": price},
            "Last Updated": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    requests.patch(url, headers=headers, json=data)

def main():
    # 1. Query the database to get all stock symbols and their page IDs
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(query_url, headers=headers)
    rows = res.json().get("results", [])

    for row in rows:
        # Assumes the 'Name' column contains the Symbol (e.g., 'ENGRO')
        symbol = row["properties"]["Name"]["title"][0]["text"]["content"]
        page_id = row["id"]
        
        print(f"Updating {symbol}...")
        current_price = get_stock_price(symbol)
        
        if current_price:
            update_notion_row(page_id, current_price)
            print(f"Success: {symbol} updated to {current_price}")

if __name__ == "__main__":
    main()
