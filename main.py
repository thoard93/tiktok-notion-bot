import os
import json
import asyncio
import base64
import httpx
from datetime import datetime, timedelta
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import anthropic
import random

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = "26d2b61d-84d1-8029-969d-d25728061db8"  # Chelsea's database

# Notion API version that supports multi-data-source databases
NOTION_API_VERSION = "2022-06-28"  # Will be overridden in headers

# This will be populated dynamically from Notion
CHELSEA_PRODUCTS = []
NEW_SAMPLE_PRODUCTS = []

# Hardcoded fallback list (used if Notion fetch fails)
FALLBACK_PRODUCTS = [
    "Physicians Choice bundle", "Calm Magnesium Gummies", "Spylt Protein Milk", 
    "Carnivore Electrolytes", "Peach Slices", "Flexi Shower Cap", "Medicube Kojic Acid",
    "Lemme Tone Gummies", "Rice Toner", "Cat Litter Deodorizer", "Colourpop X Shrek Palette",
    "Turkesterone", "Beplain Mung Bean Set", "Color Wow Dreamcoat", "Pure Peak Thyroid",
    "Sttes Perfume - Sunshine", "Choco Musk", "GNC NMN", "GNC 40+ Vitapak", "GNC Mega Men 40+",
    "Glow recipe skincare bundle", "Laura Gellar coverage concealer", "Kitsch x Grinch Hair Perfume",
    "Gopure Firming Cream", "Arterra Dog Multivitamin", "Probioderm Skincare set", "Oxygreens",
    "Yak Cheese", "Honest Chew Toy", "Cubby Litter Box", "SuperBeets", "Boka toothpaste 3pack",
    "Unbrush Hair Brush", "R+CO badlands Dry Shampoo", "dog wishbone trio", "suavecito pomade",
    "Buttah skincare set", "Hair miracle leave-in", "Konjac Jelly", "Longwear Lip Liner",
    "Redness Reform", "Niagen NAD+", "Kitsch vanilla hair perfume", "Iris electronics bags",
    "Charcoal whitener powder", "Round Lab sun cushion", "bye bye bloat", "period cramp relief gummies",
    "Car jump starter", "High roller ingrown tonic", "REVO smart cupper device", "ANANKE snapback hat",
    "Leisure hydration lemonade", "EZ bombs Tingabomb", "MAKE Luminous eyeshadow", "Prequel quench duo",
    "Dr melaxin Non-eyebag duo", "Resetting mineral powder", "Mask fit setting spray",
    "Wavytalk cool curl styler", "Disney Princess tumbler", "Bluey cookbook", "Glutathione Direct",
    "Liquid IV Variety", "Swish Mouthwash", "Cat Pheromone Diffuser", "Topicals Hair Roller",
    "iris steel necklace", "Glow trio glass skin set", "refresh intimate body wash", "PHlush stick",
    "Nutricost Creatine", "Hims wrinkle set", "Holiday Dr Squatch", "Dr Squatch Cologne + LIp balm set",
    "R&W Carpet Shampoo", "EYE-con Essentials Trio", "Rice water ultimate makeup trio",
    "Clinique honey lip & eye bundle", "Sage kids water bottle - Stitch", "Salt & stone scent duo",
    "REJURAN ampoule PDRN", "Do or Drink: Party card game", "Holiday lash essentials",
    "Mini blush set - Patrick Ta beauty", "Neutrogena Tate hydration set", "Lactic acid foaming body polish",
    "Cinnamon cow warmies", "Tula's cult classic bundle", "Kahi eye balm brightener stick",
    "Cata-kor for hair skin nails", "Zak Water Bottle", "Clean skin holiday towels XL",
    "its a 10 haircare miracle blow dry", "Bloom curve sculpt pack", "MAELYS belly firming cream",
    "Vitauthority bone broth", "Mixsoon full care set", "Embers + Haze mini eyeshadow",
    "Bask & Lather ultimate growth set", "Glow recipe cheek & lip kit", "Colorgram blurry lip duo",
    "Burst oral probiotic", "MAKE perfect blend bundle", "Bloom Creatine monohydrate",
    "Tirtir BDRN brightening eye set", "PHLUR whipped berry perfume duo", "Blush & bake puff set",
    "Laneige glaze lip duo", "Scrubzz Bathing Wipes", "Lume Whole Body Deo", "Iris Backpack",
    "Grateful Earth Mushroom Coffee", "LOVE CORN Variety Pack", "Coconu Massage Oil",
    "Leefar Feminine Probiotics", "Colorgram Fruity Glass Tint", "MOSH Protein Bars",
    "Hims Goodnight Wrinkle Cream", "VEV 14-in-1 Magnesium", "Kitsch Dermaplaners",
    "Hims Thick Fix Shampoo + Conditioner", "PAGEVINE Rotating Eyeliner Stamp Pen",
    "SKIN1004 Poremizing Clay Mask", "Grateful Earth Coconut + Turmeric",
    "Joyspring Kids Bundle (Lingo Leap + Calmity)", "Legion Whey+ Protein", "Ayoh Foods Starter Pack",
    "Mouthology Toothpaste", "Beam Dream Pumpkin Spiced Cocoa", "Beam Dream Nighttime Cocoa",
    "TryBello Hair Helper Spray", "BOLDIFY Hairline Powder Sample Kit", "All Day Complexion Set",
    "Anker Nano Power Bank", "MOSH Raspberry White Chocolate", "Prequel HALF and HALF",
    "burst expanding dental floss", "Dr Melaxin Blowout Routine Set", "Rainbow Light Men's Multi",
    "Salud Cucumber Lime", "Lemme Purr Gummies", "Davids Starter kit - Hydroxi Whitening",
    "Artnaturals Magnesium oil Spray", "PowderPal Multipurpose Scoop", "Beamach Toothpaste",
    "Natural Digestive Support Capsules", "Liposomal Glutathione", "Tokyo Mega Live Exclusive Bundle",
    "Zak Steel Tumbler", "Ranch Fuel Energy Drinks", "Nature's Sunshine Lymphatic Drainage Supplement",
    "Sungboon Serum + Retinol cream", "GHOST Greens Powder", "Nooni Korean Apple Lip Taint",
    "Hand Warmers", "Mighty Paws Chicken Jerky", "STASIS Day & Night Set", "Viking Revolution 8 Pack",
    "Wake Up Water", "VEV D3K2", "NTONPOWER Strip", "Sunny health Ab Cruncher", "6 Pack RopeRoller",
    "Feminine Freshness Bundle", "multipeptide Serum for Hair Density", "Extra Strength Rosemary Fenugreek",
    "Viking Revolution Beard Filling Pen", "Gurunanda Whitening Strips", "Rinseroo Tub Sprayer",
    "NTONPOWER Travel Strip", "Naked Neroli", "MicroIngredients NMN Complex", "AD Life Gut Detox",
    "vita 3 serum 2 pack", "Waterproof Mattress Protector", "Neuro Sugar Free", "Clear 3 Skin Support",
    "Natural Tallow Deoderant", "Be Amazing Vegan Protein", "Optimum Nutrition Whey Protein",
    "Tress complete waxing kit", "Black Forest Cocoa Flavanols", "The Ordinary Discovery Set",
    "Overthinker's Book", "Far Out Five Set", "Nutricost Turkesterone", "MOSH Cookie Dough Crunch",
    "Goat Milk Brutus Broth", "LeBanta Oil", "Peak Revival Muscle Stack", "RoC Skincare Multi Correxion",
    "Centella deep cleanse & pore set", "ALODERMA Aloe Vera Gel", "SACHEU All Day DUO",
    "SACHEU Lip STAY-N TRIO", "Retinal Sandwich Duo", "Holiday RED-Y OR NOT DUO",
    "Pout Preserve Party of 4", "COSRX Vitamin c lip plump", "Clocky Alarm Clock",
    "Freezball dog chew bone", "BLANC Cover cream stick", "Solaray Vitamin D3+K2",
    "COSRX Vitamin C toner", "Herbalista hair care bundle", "Embarouge luxe Parfum",
    "Healfast Scar Gel", "Cure Hydration Mix", "Alpha Grillers Meat Thermometer",
    "Moonforest Tapioca Cat Litter", "URO Metabolism"
]

# TikTok accounts in priority order
TIKTOK_ACCOUNTS = ["Gymgoer1993", "Dealrush93", "Datburgershop93"]

# Session storage for collecting screenshots
user_sessions = {}


async def fetch_chelsea_products_from_notion() -> tuple[list[str], list[str]]:
    """Fetch all unique products from Notion and identify New Sample products (via checkbox)"""
    global CHELSEA_PRODUCTS, NEW_SAMPLE_PRODUCTS
    
    all_products = set()
    new_samples = set()  # Products with New Sample checkbox checked
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # First, get all available product options from the database schema
        response = await client.get(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
            headers=headers
        )
        
        if response.status_code == 200:
            db_data = response.json()
            products_schema = db_data.get("properties", {}).get("Products", {})
            if products_schema.get("type") == "multi_select":
                for option in products_schema.get("multi_select", {}).get("options", []):
                    all_products.add(option.get("name"))
        else:
            print(f"Error fetching Notion database schema: {response.status_code} - {response.text}")
            print(f"Database ID: {NOTION_DATABASE_ID}")
            print(f"API Key present: {bool(NOTION_API_KEY)}")
            return [], []  # Return empty to trigger fallback
        
        # Query entries with New Sample checkbox checked
        has_more = True
        start_cursor = None
        
        while has_more:
            body = {
                "page_size": 100,
                "filter": {
                    "property": "New Sample",
                    "checkbox": {
                        "equals": True
                    }
                }
            }
            if start_cursor:
                body["start_cursor"] = start_cursor
            
            response = await client.post(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                headers=headers,
                json=body
            )
            
            if response.status_code != 200:
                print(f"Error querying Notion for new samples: {response.text}")
                break
            
            data = response.json()
            
            for page in data.get("results", []):
                props = page.get("properties", {})
                products_prop = props.get("Products", {})
                
                if products_prop.get("type") == "multi_select":
                    for item in products_prop.get("multi_select", []):
                        product_name = item.get("name")
                        if product_name:
                            new_samples.add(product_name)
                            print(f"New sample: {product_name}")
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
    
    CHELSEA_PRODUCTS = list(all_products)
    NEW_SAMPLE_PRODUCTS = list(new_samples)
    
    print(f"Loaded {len(CHELSEA_PRODUCTS)} products, {len(NEW_SAMPLE_PRODUCTS)} are new samples")
    return CHELSEA_PRODUCTS, NEW_SAMPLE_PRODUCTS


class NotionClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def get_entries_by_date(self, due_date: str) -> list[str]:
        """Get all page IDs for entries with a specific due date for our TikTok accounts"""
        page_ids = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            has_more = True
            start_cursor = None
            
            # Our specific TikTok accounts to manage
            our_accounts = ["Gymgoer1993", "Dealrush93", "Datburgershop93"]
            
            while has_more:
                body = {
                    "page_size": 100,
                    "filter": {
                        "and": [
                            {
                                "property": "Due Date",
                                "date": {
                                    "equals": due_date
                                }
                            },
                            {
                                "or": [
                                    {"property": "TikTok Account", "select": {"equals": account}}
                                    for account in our_accounts
                                ]
                            }
                        ]
                    }
                }
                if start_cursor:
                    body["start_cursor"] = start_cursor
                
                response = await client.post(
                    f"{self.base_url}/databases/{NOTION_DATABASE_ID}/query",
                    headers=self.headers,
                    json=body
                )
                
                if response.status_code != 200:
                    print(f"Error querying Notion for deletion: {response.text}")
                    break
                
                data = response.json()
                for page in data.get("results", []):
                    page_ids.append(page["id"])
                
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
        
        return page_ids
    
    async def get_old_entries_for_accounts(self) -> list[str]:
        """Get all page IDs for entries with a due date on or before today for our 3 accounts.
        This catches all stale entries from previous days that were never cleaned up."""
        page_ids = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            has_more = True
            start_cursor = None
            
            our_accounts = ["Gymgoer1993", "Dealrush93", "Datburgershop93"]
            
            while has_more:
                body = {
                    "page_size": 100,
                    "filter": {
                        "and": [
                            {
                                "property": "Due Date",
                                "date": {
                                    "on_or_before": today
                                }
                            },
                            {
                                "or": [
                                    {"property": "TikTok Account", "select": {"equals": account}}
                                    for account in our_accounts
                                ]
                            }
                        ]
                    }
                }
                if start_cursor:
                    body["start_cursor"] = start_cursor
                
                response = await client.post(
                    f"{self.base_url}/databases/{NOTION_DATABASE_ID}/query",
                    headers=self.headers,
                    json=body
                )
                
                if response.status_code != 200:
                    print(f"Error querying Notion for old entries: {response.text}")
                    break
                
                data = response.json()
                for page in data.get("results", []):
                    page_ids.append(page["id"])
                
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
        
        return page_ids
    
    async def delete_page(self, page_id: str) -> bool:
        """Archive (delete) a page"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json={"archived": True}
            )
            return response.status_code == 200
    
    async def delete_entries_by_date(self, due_date: str) -> int:
        """Delete all entries for a specific date, returns count deleted"""
        print(f"Looking for entries to delete with due date: {due_date}")
        page_ids = await self.get_entries_by_date(due_date)
        print(f"Found {len(page_ids)} entries to delete")
        deleted = 0
        
        for page_id in page_ids:
            if await self.delete_page(page_id):
                deleted += 1
                print(f"Deleted page {page_id}")
            await asyncio.sleep(0.2)  # Rate limiting
        
        print(f"Successfully deleted {deleted} entries")
        return deleted
    
    async def delete_old_entries(self) -> int:
        """Delete all old entries (due date on or before today) for our 3 accounts.
        Returns the count of old entries deleted."""
        print(f"Looking for old entries to clean up (due date on or before today)...")
        page_ids = await self.get_old_entries_for_accounts()
        print(f"Found {len(page_ids)} old entries to clean up")
        deleted = 0
        
        for page_id in page_ids:
            if await self.delete_page(page_id):
                deleted += 1
                print(f"Cleaned up old page {page_id}")
            await asyncio.sleep(0.2)  # Rate limiting
        
        print(f"Successfully cleaned up {deleted} old entries")
        return deleted
    
    async def create_page(self, product: str, video_style: str, account: str, due_date: str, is_new_sample: bool = False):
        """Create a single page in the Notion database"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": {
                    "Amount of vids": {
                        "title": [{"text": {"content": "1"}}]
                    },
                    "Creator": {
                        "select": {"name": "Chelsea"}
                    },
                    "Products": {
                        "multi_select": [{"name": product}]
                    },
                    "Video Style": {
                        "select": {"name": video_style}
                    },
                    "TikTok Account": {
                        "select": {"name": account}
                    },
                    "Status": {
                        "status": {"name": "Not Started"}
                    },
                    "Due Date": {
                        "date": {"start": due_date}
                    },
                    "New Sample": {
                        "checkbox": is_new_sample
                    }
                }
            }
            
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"Error creating page: {response.status_code} - {response.text}")
                print(f"Product: {product}, Style: {video_style}, Account: {account}")
            
            return response.status_code == 200

    async def add_product_to_schema(self, product_name: str, color: str = "purple") -> bool:
        """
        Check if product exists in schema. 
        Note: We can't update schema via API when there are >100 options (Notion limit).
        New products will be auto-created when we create the entry.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get current schema to check if product exists
            response = await client.get(
                f"{self.base_url}/databases/{NOTION_DATABASE_ID}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                print(f"Error fetching database schema: {response.status_code} - {response.text}")
                # Continue anyway - entry creation will handle it
                return True
            
            db_data = response.json()
            products_schema = db_data.get("properties", {}).get("Products", {})
            current_options = products_schema.get("multi_select", {}).get("options", [])
            
            # Check if product already exists
            existing_names = [opt.get("name", "").lower() for opt in current_options]
            if product_name.lower() in existing_names:
                print(f"Product '{product_name}' already exists in schema")
                return True
            
            # Product doesn't exist - it will be auto-created when we make the entry
            # (Can't update schema via API when >100 options exist - Notion limit)
            print(f"Product '{product_name}' is new - will be auto-added when entry is created")
            return True

    async def create_new_sample_entry(self, product_name: str) -> bool:
        """Create a placeholder entry with New Sample checkbox checked"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            data = {
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": {
                    "Amount of vids": {
                        "title": [{"text": {"content": "1"}}]
                    },
                    "Creator": {
                        "select": {"name": "Chelsea"}
                    },
                    "Products": {
                        "multi_select": [{"name": product_name}]
                    },
                    "Video Style": {
                        "select": {"name": "Talking"}
                    },
                    "TikTok Account": {
                        "select": {"name": "Gymgoer1993"}
                    },
                    "Status": {
                        "status": {"name": "Not Started"}
                    },
                    "Due Date": {
                        "date": {"start": tomorrow}
                    },
                    "New Sample": {
                        "checkbox": True
                    }
                }
            }
            
            print(f"Creating new sample entry for '{product_name}'...")
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"Error creating new sample entry for '{product_name}': {response.status_code} - {response.text}")
                return False
            
            print(f"✓ Created new sample entry for '{product_name}'")
            return True


def detect_image_type(image_bytes: bytes) -> str:
    """Detect image MIME type from bytes"""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    elif image_bytes[:2] == b'\xff\xd8':
        return "image/jpeg"
    elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    else:
        # Default to JPEG as Telegram usually sends JPEG
        return "image/jpeg"


async def process_screenshots_with_claude(screenshots: list[bytes], inventory_list: list[str]) -> list[dict]:
    """Use Claude to OCR and extract product sales data from screenshots, matching to inventory"""
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare images for Claude
    image_content = []
    for i, screenshot in enumerate(screenshots):
        base64_image = base64.standard_b64encode(screenshot).decode("utf-8")
        media_type = detect_image_type(screenshot)
        image_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_image
            }
        })
    
    # Create inventory list string for Claude
    inventory_str = "\n".join(f"- {p}" for p in inventory_list)
    
    image_content.append({
        "type": "text",
        "text": f"""Analyze these TikTok Shop earnings screenshots. Extract ALL products shown with their units sold.

IMPORTANT: Match each product to the closest item from this inventory list when possible. Only match if you're confident it's the same product (same brand AND same product type). Different products from the same brand should NOT match.

INVENTORY LIST:
{inventory_str}

Return a JSON array of objects with this format:
[
    {{"product_name": "exact name as shown in screenshot", "units_sold": number, "inventory_match": "matching inventory item or null if no match"}},
    ...
]

Examples of CORRECT matching:
- "Nooni Korean Apple Lip Tint Stain Duo" -> "Nooni Korean Apple Lip Taint" (same product)
- "Freezball - Durable Fillable Dog Chew Bone" -> "Freezball dog chew bone" (same product)
- "HonestChew - Free from Petroleum" -> "Honest Chew Toy" (same product)

Examples of INCORRECT matching (don't do this):
- "Color Wow Speed Dry Blow-Dry Spray" -> "Color Wow Dreamcoat" (WRONG - different products!)
- "GNC Mega Men Sport" -> "GNC Mega Men 40+" (WRONG - different products!)

Sort by units_sold descending (highest first). Include ALL products visible.
Only return the JSON array, no other text."""
    })
    
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": image_content
        }]
    )
    
    # Parse the response
    try:
        result_text = response.content[0].text
        # Clean up potential markdown formatting
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        products = json.loads(result_text.strip())
        return products
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing Claude response: {e}")
        return []


def match_products_to_inventory(extracted_products: list[dict], inventory_list: list[str]) -> list[dict]:
    """Use Claude's inventory matching from OCR step"""
    matched = []
    
    for product in extracted_products:
        inventory_match = product.get("inventory_match")
        units = product.get("units_sold", 0)
        
        if inventory_match and inventory_match in inventory_list:
            matched.append({
                "product": inventory_match,
                "units_sold": units,
                "in_inventory": True,
                "original_name": product.get("product_name", "")
            })
        else:
            matched.append({
                "product": product.get("product_name", "Unknown"),
                "units_sold": units,
                "in_inventory": False,
                "original_name": product.get("product_name", "")
            })
    
    return matched


def generate_daily_lineup(matched_products: list[dict], new_samples: list[str]) -> dict:
    """Generate the daily video lineup for all 3 accounts
    
    New Sample Distribution:
    - Gymgoer1993 gets ALL new samples (up to 7 max)
    - Dealrush93 gets overflow if more than 7 new samples
    - Datburgershop93 gets remaining overflow
    - Remaining slots filled with top sellers from earnings
    """
    
    # Separate products Chelsea has vs doesn't have
    available_products = [p for p in matched_products if p["in_inventory"]]
    # Sort by units_sold, treating None as 0
    available_products.sort(key=lambda x: x["units_sold"] if x["units_sold"] is not None else 0, reverse=True)
    
    # Remove new samples from the selling products list (they'll be added separately)
    selling_products = [p for p in available_products if p["product"] not in new_samples]
    
    # Distribute new samples across accounts (Gymgoer gets priority)
    new_samples_copy = new_samples.copy()
    account_new_samples = {
        "Gymgoer1993": [],
        "Dealrush93": [],
        "Datburgershop93": []
    }
    
    # Gymgoer1993 gets all new samples up to 7
    while new_samples_copy and len(account_new_samples["Gymgoer1993"]) < 7:
        account_new_samples["Gymgoer1993"].append(new_samples_copy.pop(0))
    
    # Dealrush93 gets overflow up to 7
    while new_samples_copy and len(account_new_samples["Dealrush93"]) < 7:
        account_new_samples["Dealrush93"].append(new_samples_copy.pop(0))
    
    # Datburgershop93 gets remaining overflow up to 7
    while new_samples_copy and len(account_new_samples["Datburgershop93"]) < 7:
        account_new_samples["Datburgershop93"].append(new_samples_copy.pop(0))
    
    lineup = {}
    
    for account_idx, account in enumerate(TIKTOK_ACCOUNTS):
        # Determine products and videos needed per account
        if account == "Gymgoer1993":
            products_needed = 5  # 15 videos: 5 products × 3 videos each
            videos_per_account = 15
        else:  # Dealrush93 and Datburgershop93
            products_needed = 4   # 10 videos: 3 products × 3 videos + 1 product × 1 video
            videos_per_account = 10
        
        selected = []
        
        # First, add new samples for this account
        for sample in account_new_samples[account]:
            selected.append({
                "product": sample,
                "units_sold": 0,
                "source": "new_sample"
            })
        
        # Determine start index for selling products based on account
        # This creates variety across accounts
        if account == "Gymgoer1993":
            start_idx = 0  # Top sellers
        elif account == "Dealrush93":
            start_idx = 3  # Offset for variety
        else:  # Datburgershop93
            start_idx = 6  # More offset
        
        # Fill remaining slots with selling products
        products_in_selected = [s["product"] for s in selected]
        seller_idx = start_idx
        
        while len(selected) < products_needed and seller_idx < len(selling_products) + start_idx:
            actual_idx = seller_idx % len(selling_products) if selling_products else 0
            if not selling_products:
                break
                
            if actual_idx < len(selling_products):
                product = selling_products[actual_idx]["product"]
                if product not in products_in_selected:
                    selected.append({
                        "product": product,
                        "units_sold": selling_products[actual_idx]["units_sold"],
                        "source": "selling"
                    })
                    products_in_selected.append(product)
            seller_idx += 1
        
        # Fill any remaining slots with random rotation products
        remaining_inventory = [p for p in CHELSEA_PRODUCTS if p not in products_in_selected and p not in new_samples]
        random.shuffle(remaining_inventory)
        
        while len(selected) < products_needed and remaining_inventory:
            product = remaining_inventory.pop()
            selected.append({
                "product": product,
                "units_sold": 0,
                "source": "rotation"
            })
        
        # Generate video entries per account
        # Format: Most products get 3 videos (2 Sound Method + 1 MOF), last product gets remaining videos
        videos = []
        
        # Determine MOF style based on account
        if account == "Gymgoer1993":
            mof_style = "Crying MOF"
            # Gymgoer: 15 videos = 5 products × 3 videos each
            products_with_3_videos = 5
        else:  # Dealrush93 and Datburgershop93
            mof_style = "Snapchat MOF"
            # Others: 10 videos = 3 products × 3 videos + 1 product × 1 video
            products_with_3_videos = 3
        
        for i, product_info in enumerate(selected):
            product = product_info["product"]
            is_new_sample = product_info["source"] == "new_sample"
            
            if i < products_with_3_videos:  # Most products get 3 videos each
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
                videos.append({"product": product, "style": mof_style, "is_new_sample": is_new_sample})
            else:  # Last product gets remaining videos (1 video)
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
        
        lineup[account] = {
            "products": selected,
            "videos": videos,
            "new_sample_count": len(account_new_samples[account])
        }
    
    return lineup


def format_lineup_preview(lineup: dict, due_date: str) -> str:
    """Format the lineup for Telegram preview"""
    message = f"📋 *Proposed Video Lineup for {due_date}*\n\n"
    
    total_videos = 0
    total_new_samples = 0
    
    for account in TIKTOK_ACCOUNTS:
        data = lineup[account]
        new_sample_count = data.get("new_sample_count", 0)
        total_new_samples += new_sample_count
        video_count = len(data["videos"])
        
        message += f"*{account}* ({video_count} videos"
        if new_sample_count > 0:
            message += f", {new_sample_count} new samples"
        message += ")\n"
        message += "─" * 25 + "\n"
        
        for i, product_info in enumerate(data["products"]):
            if product_info["source"] == "new_sample":
                emoji = "🆕"
                units = "(NEW SAMPLE)"
            elif product_info["source"] == "selling":
                emoji = "🔥"
                units = f"({product_info['units_sold']} sold)"
            else:
                emoji = "🔄"
                units = "(rotation)"
            
            # Determine video count for this product
            if account == "Gymgoer1993":
                video_count = 3 if i < 5 else 1  # All 5 products get 3 videos
            else:  # Dealrush93 and Datburgershop93
                video_count = 3 if i < 3 else 1  # 3 products get 3 videos, last gets 1
            
            message += f"{emoji} {product_info['product']}\n"
            message += f"   └ {video_count} videos {units}\n"
        
        message += "\n"
        total_videos += len(data["videos"])
    
    message += f"*Total: {total_videos} videos*\n"
    if total_new_samples > 0:
        message += f"*New Samples Being Tested: {total_new_samples}*\n"
    message += "\nReply *confirm* to create in Notion, or *cancel* to abort."
    
    return message


async def create_notion_entries(lineup: dict, due_date: str) -> tuple[int, int, int, int]:
    """Create all Notion entries for the lineup, replacing any existing entries for that date.
    Also cleans up old entries from previous days for the 3 accounts.
    Returns (success, failed, deleted_for_date, old_cleaned_up)"""
    notion = NotionClient(NOTION_API_KEY)
    
    # First, clean up old entries from previous days (due date on or before today)
    old_cleaned = await notion.delete_old_entries()
    
    # Then, delete any existing entries for tomorrow's date (in case of re-run)
    deleted = await notion.delete_entries_by_date(due_date)
    
    success = 0
    failed = 0
    
    for account in TIKTOK_ACCOUNTS:
        for video in lineup[account]["videos"]:
            try:
                result = await notion.create_page(
                    product=video["product"],
                    video_style=video["style"],
                    account=account,
                    due_date=due_date,
                    is_new_sample=video.get("is_new_sample", False)
                )
                if result:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error creating Notion page: {e}")
                failed += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.3)
    
    return success, failed, deleted, old_cleaned


# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 *TikTok Shop Video Automation Bot*\n\n"
        "Send me your daily earnings screenshots from TikTok Shop.\n\n"
        "*Video Lineup Commands:*\n"
        "/start - Show this message\n"
        "/generate - Process screenshots and generate lineup\n"
        "/newsample - Add new sample products from screenshots\n"
        "/clear - Clear current screenshots\n"
        "/status - Check how many screenshots collected\n\n"
        "*Outreach Commands:*\n"
        "/outreach - Scan Gmail for new brand outreach\n"
        "/outreachstats - View outreach statistics\n"
        "/setrate - Change default retainer rate\n\n"
        "Just send screenshots, then use /generate when ready!",
        parse_mode="Markdown"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"screenshots": [], "lineup": None, "mode": "earnings"}
    
    # Check if in new sample mode
    if user_sessions[user_id].get("mode") == "newsample":
        await process_new_sample_photo(update, context)
        return
    
    # Normal earnings screenshot handling
    # Download the photo
    photo = update.message.photo[-1]  # Get highest resolution
    file = await context.bot.get_file(photo.file_id)
    
    photo_bytes = await file.download_as_bytearray()
    user_sessions[user_id]["screenshots"].append(bytes(photo_bytes))
    
    count = len(user_sessions[user_id]["screenshots"])
    await update.message.reply_text(
        f"📸 Screenshot {count} received!\n\n"
        f"Send more or use /generate when you've sent all screenshots."
    )


async def newsample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new sample mode - user sends screenshots of new samples to add"""
    user_id = update.effective_user.id
    
    user_sessions[user_id] = {
        "screenshots": [],
        "lineup": None,
        "mode": "newsample",
        "sample_photos": []
    }
    
    await update.message.reply_text(
        "🆕 *New Sample Mode*\n\n"
        "Send me screenshots of your new sample products from TikTok Shop.\n"
        "I'll extract the product names, shorten them, and add them to Notion with a purple tag.\n\n"
        "Send your screenshots, then type /addsample when ready!\n"
        "Use /clear to cancel.",
        parse_mode="Markdown"
    )


async def process_new_sample_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos in new sample mode"""
    user_id = update.effective_user.id
    
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    if "sample_photos" not in user_sessions[user_id]:
        user_sessions[user_id]["sample_photos"] = []
    
    user_sessions[user_id]["sample_photos"].append(bytes(photo_bytes))
    
    count = len(user_sessions[user_id]["sample_photos"])
    await update.message.reply_text(
        f"📸 New sample screenshot {count} received!\n\n"
        f"Send more or use /addsample when ready."
    )


async def addsample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new sample screenshots and add products to Notion"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or not user_sessions[user_id].get("sample_photos"):
        await update.message.reply_text("❌ No sample screenshots found. Use /newsample first, then send photos.")
        return
    
    await update.message.reply_text("🔄 Analyzing screenshots for product names...")
    
    try:
        # Extract product names from screenshots using Claude
        sample_photos = user_sessions[user_id]["sample_photos"]
        extracted_products = await extract_new_sample_products(sample_photos)
        
        if not extracted_products:
            await update.message.reply_text(
                "❌ Couldn't extract product names from screenshots.\n"
                "Make sure the product names are visible and try again."
            )
            return
        
        await update.message.reply_text(
            f"✅ Found {len(extracted_products)} products:\n" +
            "\n".join(f"• {p}" for p in extracted_products[:10]) +
            ("\n..." if len(extracted_products) > 10 else "") +
            "\n\n🔄 Adding to Notion..."
        )
        
        # Add each product to Notion
        notion = NotionClient(api_key=NOTION_API_KEY)
        added = 0
        failed = 0
        failed_products = []
        
        for i, product in enumerate(extracted_products):
            print(f"Processing product {i+1}/{len(extracted_products)}: {product}")
            try:
                # Add to Products schema with purple color
                schema_result = await notion.add_product_to_schema(product, color="purple")
                
                if schema_result:
                    # Create entry with New Sample checkbox
                    entry_result = await notion.create_new_sample_entry(product)
                    if entry_result:
                        added += 1
                    else:
                        failed += 1
                        failed_products.append(f"{product} (entry failed)")
                else:
                    failed += 1
                    failed_products.append(f"{product} (schema failed)")
                    
                await asyncio.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"Error adding product {product}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
                failed_products.append(f"{product} (exception: {str(e)[:50]})")
        
        # Clear session
        user_sessions[user_id] = {"screenshots": [], "lineup": None, "mode": "earnings"}
        
        result_msg = f"✅ Done!\n\nAdded: {added} products\nFailed: {failed}"
        if failed_products:
            result_msg += f"\n\nFailed products:\n" + "\n".join(f"• {p}" for p in failed_products[:5])
            if len(failed_products) > 5:
                result_msg += f"\n...and {len(failed_products) - 5} more"
        
        if added > 0:
            result_msg += f"\n\n✅ New samples marked and will be prioritized in your next lineup!"
            result_msg += f"\n\n💡 Tip: You can manually change the color to purple in Notion if you want."
        
        await update.message.reply_text(result_msg)
        
    except Exception as e:
        print(f"Error in addsample: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(f"❌ Error processing samples: {str(e)}")


async def extract_new_sample_products(photos: list[bytes]) -> list[str]:
    """Use Claude to extract and shorten product names from new sample screenshots"""
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    
    # Prepare images for Claude
    image_content = []
    for screenshot in photos:
        base64_image = base64.standard_b64encode(screenshot).decode("utf-8")
        media_type = detect_image_type(screenshot)
        image_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_image
            }
        })
    
    image_content.append({
        "type": "text",
        "text": """Analyze these TikTok Shop screenshots showing new sample products.

Extract ALL product names visible and create SHORT, CLEAN versions for a database.

Rules for shortening:
- Remove unnecessary words like "for", "with", "and", "the", "pack of"
- Keep brand name if recognizable (e.g., "COSRX", "Bloom", "GNC")
- Keep key product identifier (e.g., "Vitamin C Serum", "Protein Powder")
- Target 3-6 words max
- Capitalize properly (Title Case)

Examples:
- "COSRX Advanced Snail 96 Mucin Power Essence 100ml" → "COSRX Snail Mucin Essence"
- "Bloom Nutrition Super Greens Powder Digestive Health" → "Bloom Super Greens"
- "The Original MakeUp Eraser 7-Day Set" → "MakeUp Eraser 7-Day Set"

Return ONLY a JSON array of shortened product names, nothing else:
["Product Name 1", "Product Name 2", ...]"""
    })
    
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": image_content}]
    )
    
    response_text = response.content[0].text.strip()
    
    # Parse JSON response (same pattern as process_screenshots_with_claude)
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        response_text = response_text.strip()
        
        products = json.loads(response_text)
        return products if isinstance(products, list) else []
    except json.JSONDecodeError as e:
        print(f"Error parsing Claude response: {e}")
        print(f"Response was: {response_text}")
        return []


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process screenshots and generate lineup"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or not user_sessions[user_id]["screenshots"]:
        await update.message.reply_text("❌ No screenshots found. Send some first!")
        return
    
    await update.message.reply_text("🔄 Fetching latest products from Notion...")
    
    try:
        # Fetch products dynamically from Notion
        all_products, new_samples = await fetch_chelsea_products_from_notion()
        
        if not all_products:
            # Fall back to hardcoded list if Notion fetch fails
            all_products = FALLBACK_PRODUCTS
            new_samples = []
            await update.message.reply_text("⚠️ Couldn't fetch from Notion, using backup product list.")
        else:
            sample_msg = f"📦 Loaded {len(all_products)} products from Notion"
            if new_samples:
                # Truncate list if too many new samples
                if len(new_samples) <= 5:
                    sample_msg += f"\n🆕 Found {len(new_samples)} NEW SAMPLES: {', '.join(new_samples)}"
                else:
                    shown = list(new_samples)[:5]
                    sample_msg += f"\n🆕 Found {len(new_samples)} NEW SAMPLES including: {', '.join(shown)}..."
            await update.message.reply_text(sample_msg)
        
        await update.message.reply_text("🔄 Processing screenshots with AI... This may take a moment.")
        
        # Process screenshots with Claude (now with inventory list for smart matching)
        screenshots = user_sessions[user_id]["screenshots"]
        extracted_products = await process_screenshots_with_claude(screenshots, all_products)
        
        if not extracted_products:
            await update.message.reply_text(
                "❌ Couldn't extract products from screenshots. "
                "Please make sure the earnings data is visible and try again."
            )
            return
        
        await update.message.reply_text(f"✅ Found {len(extracted_products)} products in earnings!")
        
        # Match to Chelsea's inventory (using Claude's smart matching)
        matched_products = match_products_to_inventory(extracted_products, all_products)
        in_inventory = sum(1 for p in matched_products if p["in_inventory"])
        
        await update.message.reply_text(
            f"📦 Matched {in_inventory} products to Chelsea's inventory.\n"
            f"🔄 {len(matched_products) - in_inventory} will use rotation products."
        )
        
        # Generate lineup with new samples
        lineup = generate_daily_lineup(matched_products, new_samples)
        
        # Calculate tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Store lineup for confirmation
        user_sessions[user_id]["lineup"] = lineup
        user_sessions[user_id]["due_date"] = tomorrow
        
        # Send preview
        preview = format_lineup_preview(lineup, tomorrow)
        await update.message.reply_text(preview, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing: {str(e)}")
        raise e


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for confirm/cancel and custom outreach rates)"""
    user_id = update.effective_user.id
    
    # Check if user is inputting a custom outreach rate
    if await handle_custom_rate_input(update, context):
        return
    
    text = update.message.text.lower().strip()
    
    if text == "confirm":
        if user_id not in user_sessions or not user_sessions[user_id].get("lineup"):
            await update.message.reply_text("❌ No lineup to confirm. Use /generate first.")
            return
        
        await update.message.reply_text("🚀 Updating Notion... This will take about 30-60 seconds.")
        
        lineup = user_sessions[user_id]["lineup"]
        due_date = user_sessions[user_id]["due_date"]
        
        success, failed, deleted, old_cleaned = await create_notion_entries(lineup, due_date)
        
        result_msg = f"✅ *Done!*\n\n"
        if old_cleaned > 0:
            result_msg += f"🧹 Cleaned up: {old_cleaned} old entries from previous days\n"
        if deleted > 0:
            result_msg += f"🗑️ Replaced: {deleted} entries for {due_date}\n"
        result_msg += f"✨ Created: {success} new entries\n"
        if failed > 0:
            result_msg += f"❌ Failed: {failed} entries\n"
        result_msg += f"\nChelsea's Notion is updated for {due_date}!"
        
        await update.message.reply_text(result_msg, parse_mode="Markdown")
        
        # Clear session
        user_sessions[user_id] = {"screenshots": [], "lineup": None}
        
    elif text == "cancel":
        if user_id in user_sessions:
            user_sessions[user_id]["lineup"] = None
        await update.message.reply_text("❌ Lineup cancelled. Send new screenshots to start over.")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear current screenshots"""
    user_id = update.effective_user.id
    user_sessions[user_id] = {"screenshots": [], "lineup": None, "mode": "earnings", "sample_photos": []}
    await update.message.reply_text("🗑️ Cleared! Ready for new screenshots.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current status"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        count = 0
        has_lineup = False
    else:
        count = len(user_sessions[user_id].get("screenshots", []))
        has_lineup = user_sessions[user_id].get("lineup") is not None
    
    status = f"📊 *Current Status*\n\n"
    status += f"Screenshots collected: {count}\n"
    status += f"Lineup generated: {'Yes ✅' if has_lineup else 'No'}"
    
    await update.message.reply_text(status, parse_mode="Markdown")


# =============================================================================
# Outreach Commands & Handlers
# =============================================================================

# Global outreach scanner reference
outreach_scanner = None


async def outreach_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger an outreach scan."""
    global outreach_scanner
    if not outreach_scanner or not outreach_scanner.is_ready:
        await update.message.reply_text("❌ Outreach scanner not configured. Check Gmail credentials.")
        return
    
    await update.message.reply_text("📧 Scanning Gmail for new brand outreach...")
    
    try:
        from outreach import send_outreach_notification
        outreach_emails = await outreach_scanner.scan_for_outreach()
        
        if not outreach_emails:
            await update.message.reply_text("✅ No new outreach found.")
            return
        
        await update.message.reply_text(f"Found {len(outreach_emails)} new outreach emails! Sending details...")
        
        for entry in outreach_emails:
            await send_outreach_notification(
                context.bot, update.effective_chat.id, entry
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error scanning outreach: {e}")
        print(f"Outreach scan error: {e}")
        import traceback
        traceback.print_exc()


async def outreachstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show outreach statistics."""
    global outreach_scanner
    if not outreach_scanner:
        await update.message.reply_text("❌ Outreach scanner not configured.")
        return
    
    try:
        stats = await outreach_scanner.tracker.get_stats()
        
        if stats is None:
            await update.message.reply_text("❌ Outreach Notion database not configured.")
            return
        
        from outreach import DEFAULT_RETAINER_RATE
        msg = (
            f"📊 *Outreach Statistics*\n\n"
            f"📧 Total outreach: {stats['total']}\n"
            f"✅ Replied: {stats['replied']}\n"
            f"❌ Declined: {stats['declined']}\n"
            f"🤝 Deals closed: {stats['deals_closed']}\n"
            f"🚨 Suspicious: {stats['suspicious']}\n\n"
            f"💰 Current rate: ${outreach_scanner.responder.default_rate} for "
            f"{outreach_scanner.responder.default_videos} videos"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching stats: {e}")


async def setrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change the default retainer rate. Usage: /setrate 600"""
    global outreach_scanner
    if not outreach_scanner:
        await update.message.reply_text("❌ Outreach scanner not configured.")
        return
    
    if not context.args or not context.args[0].isdigit():
        current = outreach_scanner.responder.default_rate
        await update.message.reply_text(
            f"💰 Current rate: ${current} for {outreach_scanner.responder.default_videos} videos\n\n"
            f"Usage: /setrate 600"
        )
        return
    
    new_rate = int(context.args[0])
    outreach_scanner.responder.default_rate = new_rate
    await update.message.reply_text(
        f"✅ Default retainer rate updated to *${new_rate}* for "
        f"{outreach_scanner.responder.default_videos} videos",
        parse_mode="Markdown"
    )


# Store users waiting to input a custom rate
custom_rate_pending = {}


async def outreach_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for outreach approval."""
    global outreach_scanner
    query = update.callback_query
    await query.answer()
    
    if not outreach_scanner:
        await query.edit_message_text("❌ Outreach scanner not configured.")
        return
    
    data = query.data
    
    if data.startswith("outreach_approve_"):
        outreach_id = data.replace("outreach_approve_", "")
        success, msg = await outreach_scanner.approve_and_reply(outreach_id)
        emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{emoji} {msg}")
    
    elif data.startswith("outreach_custom_"):
        outreach_id = data.replace("outreach_custom_", "")
        user_id = update.effective_user.id
        custom_rate_pending[user_id] = outreach_id
        await query.edit_message_text(
            f"💰 Enter your custom rate (just the number, e.g. 600):\n\n"
            f"Type the amount and send it."
        )
    
    elif data.startswith("outreach_skip_"):
        outreach_id = data.replace("outreach_skip_", "")
        success, msg = await outreach_scanner.skip_outreach(outreach_id)
        emoji = "✅" if success else "❌"
        await query.edit_message_text(f"{emoji} {msg}")
    
    elif data.startswith("outreach_scam_"):
        outreach_id = data.replace("outreach_scam_", "")
        success, msg = await outreach_scanner.mark_scam(outreach_id)
        emoji = "🚫" if success else "❌"
        await query.edit_message_text(f"{emoji} {msg}")


async def handle_custom_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is inputting a custom outreach rate. Returns True if handled."""
    global outreach_scanner
    user_id = update.effective_user.id
    
    if user_id not in custom_rate_pending:
        return False
    
    text = update.message.text.strip()
    
    if not text.replace('$', '').isdigit():
        await update.message.reply_text("❌ Please enter a valid number (e.g. 600)")
        return True
    
    rate = int(text.replace('$', ''))
    outreach_id = custom_rate_pending.pop(user_id)
    
    if outreach_scanner:
        success, msg = await outreach_scanner.approve_and_reply(outreach_id, custom_rate=rate)
        emoji = "✅" if success else "❌"
        await update.message.reply_text(f"{emoji} {msg}")
    else:
        await update.message.reply_text("❌ Outreach scanner not available.")
    
    return True


async def post_init(application):
    """Called after the application is initialized. Starts the outreach scanner."""
    global outreach_scanner
    
    try:
        from outreach import OutreachScanner, outreach_scan_loop
        
        scanner = OutreachScanner()
        if scanner.initialize():
            outreach_scanner = scanner
            
            # Get the chat ID for notifications
            chat_id = TELEGRAM_CHAT_ID
            if chat_id:
                # Start background scanning loop
                asyncio.create_task(
                    outreach_scan_loop(
                        scanner=outreach_scanner,
                        bot=application.bot,
                        chat_id=int(chat_id),
                        interval_minutes=30
                    )
                )
                print("📧 Outreach auto-scanner started (every 30 min)")
            else:
                print("⚠️ TELEGRAM_CHAT_ID not set — outreach scanner available via /outreach only")
        else:
            print("⚠️ Gmail not configured — outreach features disabled")
    except ImportError as e:
        print(f"⚠️ Outreach module not available: {e}")
    except Exception as e:
        print(f"⚠️ Error initializing outreach scanner: {e}")


def main():
    """Start the bot"""
    # Log configuration on startup
    print(f"Starting TikTok Notion Bot...")
    print(f"Database ID: {NOTION_DATABASE_ID}")
    print(f"Notion API Key present: {bool(NOTION_API_KEY)}")
    print(f"Anthropic API Key present: {bool(ANTHROPIC_API_KEY)}")
    print(f"Gmail credentials present: {bool(os.environ.get('GMAIL_REFRESH_TOKEN'))}")
    
    # Create application with post_init for outreach scanner
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers — Video lineup
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("newsample", newsample_command))
    application.add_handler(CommandHandler("addsample", addsample_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Add handlers — Outreach
    application.add_handler(CommandHandler("outreach", outreach_command))
    application.add_handler(CommandHandler("outreachstats", outreachstats_command))
    application.add_handler(CommandHandler("setrate", setrate_command))
    application.add_handler(CallbackQueryHandler(outreach_callback_handler, pattern=r'^outreach_'))
    
    # Add handlers — Messages
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
