"""
One-time script to create the Outreach Deals Notion database.
Usage: python create_outreach_db.py YOUR_NOTION_API_KEY
"""

import os
import sys
import json
import httpx
import asyncio

BASE_URL = "https://api.notion.com/v1"


def get_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }


async def find_parent_page(headers):
    """Search for available pages to use as parent for the new database."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/search",
            headers=headers,
            json={
                "filter": {"property": "object", "value": "page"},
                "page_size": 20
            }
        )
        
        if response.status_code != 200:
            print(f"Error searching Notion: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        pages = data.get("results", [])
        
        if not pages:
            print("No pages found. Make sure the Notion integration has access to at least one page.")
            return None
        
        print(f"Found {len(pages)} accessible pages, using first one.")
        return pages[0]["id"]


async def create_outreach_database(headers, parent_page_id):
    """Create the Outreach Deals database with all required properties."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        database_spec = {
            "parent": {
                "type": "page_id",
                "page_id": parent_page_id
            },
            "title": [
                {
                    "type": "text",
                    "text": {"content": "Outreach Deals"}
                }
            ],
            "properties": {
                "Brand Name": {
                    "title": {}
                },
                "Contact Email": {
                    "email": {}
                },
                "Contact Name": {
                    "rich_text": {}
                },
                "Product Type": {
                    "select": {
                        "options": [
                            {"name": "Skincare", "color": "pink"},
                            {"name": "Supplements", "color": "green"},
                            {"name": "Beauty", "color": "purple"},
                            {"name": "Fitness", "color": "orange"},
                            {"name": "Kitchen", "color": "yellow"},
                            {"name": "Fashion", "color": "blue"},
                            {"name": "Tech", "color": "gray"},
                            {"name": "Health", "color": "red"},
                            {"name": "Other", "color": "default"}
                        ]
                    }
                },
                "Offer Summary": {
                    "rich_text": {}
                },
                "Status": {
                    "select": {
                        "options": [
                            {"name": "New", "color": "blue"},
                            {"name": "Replied", "color": "yellow"},
                            {"name": "Declined", "color": "red"},
                            {"name": "Scam", "color": "gray"},
                            {"name": "Deal Closed", "color": "green"}
                        ]
                    }
                },
                "Date Received": {
                    "date": {}
                },
                "Date Replied": {
                    "date": {}
                },
                "Retainer Amount": {
                    "number": {
                        "format": "dollar"
                    }
                },
                "Suspicious": {
                    "checkbox": {}
                }
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/databases",
            headers=headers,
            json=database_spec
        )
        
        if response.status_code != 200:
            print(f"Error creating database: {response.status_code}")
            print(response.text)
            return None
        
        result = response.json()
        db_id = result["id"]
        print(f"{'=' * 60}")
        print(f"SUCCESS! Outreach Deals database created!")
        print(f"{'=' * 60}")
        print(f"Database ID: {db_id}")
        print(f"")
        print(f"Add this to Render environment variables:")
        print(f"  OUTREACH_NOTION_DB_ID={db_id}")
        print(f"{'=' * 60}")
        return db_id


async def main():
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NOTION_API_KEY")
    
    if not api_key:
        print("Usage: python create_outreach_db.py YOUR_NOTION_API_KEY")
        return
    
    headers = get_headers(api_key)
    
    print("Searching for a parent page...")
    parent_id = await find_parent_page(headers)
    
    if not parent_id:
        return
    
    print(f"Creating Outreach Deals database...")
    await create_outreach_database(headers, parent_id)


if __name__ == "__main__":
    asyncio.run(main())
