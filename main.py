import os
import json
import asyncio
import base64
import httpx
from datetime import datetime, timedelta
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic
import random

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = "26d2b61d84d18029969dd25728061db8"  # Chelsea's database (no dashes)

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
    """Fetch all unique products from Notion and identify New Sample products"""
    global CHELSEA_PRODUCTS, NEW_SAMPLE_PRODUCTS
    
    all_products = set()
    new_samples = set()
    
    async with httpx.AsyncClient() as client:
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
        
        # Now query the database to find which products are marked as New Sample
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
                print(f"Error fetching from Notion: {response.text}")
                break
            
            data = response.json()
            
            for page in data.get("results", []):
                props = page.get("properties", {})
                
                # Get products from multi-select for New Sample entries
                products_prop = props.get("Products", {})
                if products_prop.get("type") == "multi_select":
                    for item in products_prop.get("multi_select", []):
                        product_name = item.get("name")
                        if product_name:
                            new_samples.add(product_name)
            
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
        """Get all page IDs for entries with a specific due date"""
        page_ids = []
        async with httpx.AsyncClient() as client:
            has_more = True
            start_cursor = None
            
            while has_more:
                body = {
                    "page_size": 100,
                    "filter": {
                        "property": "Due Date",
                        "date": {
                            "equals": due_date
                        }
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
                    print(f"Error querying Notion: {response.text}")
                    break
                
                data = response.json()
                for page in data.get("results", []):
                    page_ids.append(page["id"])
                
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
        
        return page_ids
    
    async def delete_page(self, page_id: str) -> bool:
        """Archive (delete) a page"""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json={"archived": True}
            )
            return response.status_code == 200
    
    async def delete_entries_by_date(self, due_date: str) -> int:
        """Delete all entries for a specific date, returns count deleted"""
        page_ids = await self.get_entries_by_date(due_date)
        deleted = 0
        
        for page_id in page_ids:
            if await self.delete_page(page_id):
                deleted += 1
            await asyncio.sleep(0.2)  # Rate limiting
        
        return deleted
    
    async def create_page(self, product: str, video_style: str, account: str, due_date: str, is_new_sample: bool = False):
        """Create a single page in the Notion database"""
        async with httpx.AsyncClient() as client:
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
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
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
    
    response = client.messages.create(
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
    available_products.sort(key=lambda x: x["units_sold"], reverse=True)
    
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
        products_needed = 7
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
        
        # Generate video entries (20 per account)
        # 6 products x 3 videos + 1 product x 2 videos = 20 videos
        videos = []
        for i, product_info in enumerate(selected):
            product = product_info["product"]
            is_new_sample = product_info["source"] == "new_sample"
            
            if i < 6:  # First 6 products get 3 videos each
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
                videos.append({"product": product, "style": "MOF", "is_new_sample": is_new_sample})
            else:  # Last product gets 2 videos
                videos.append({"product": product, "style": "Sound Method", "is_new_sample": is_new_sample})
                videos.append({"product": product, "style": "MOF", "is_new_sample": is_new_sample})
        
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
        
        message += f"*{account}* (20 videos"
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
            
            video_count = 3 if i < 6 else 2
            message += f"{emoji} {product_info['product']}\n"
            message += f"   └ {video_count} videos {units}\n"
        
        message += "\n"
        total_videos += len(data["videos"])
    
    message += f"*Total: {total_videos} videos*\n"
    if total_new_samples > 0:
        message += f"*New Samples Being Tested: {total_new_samples}*\n"
    message += "\nReply *confirm* to create in Notion, or *cancel* to abort."
    
    return message


async def create_notion_entries(lineup: dict, due_date: str) -> tuple[int, int, int]:
    """Create all Notion entries for the lineup, replacing any existing entries for that date"""
    notion = NotionClient(NOTION_API_KEY)
    
    # First, delete any existing entries for this date
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
    
    return success, failed, deleted


# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 *TikTok Shop Video Automation Bot*\n\n"
        "Send me your daily earnings screenshots from TikTok Shop.\n\n"
        "*Commands:*\n"
        "/start - Show this message\n"
        "/generate - Process screenshots and generate lineup\n"
        "/clear - Clear current screenshots\n"
        "/status - Check how many screenshots collected\n\n"
        "Just send screenshots, then use /generate when ready!",
        parse_mode="Markdown"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos"""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {"screenshots": [], "lineup": None}
    
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
                sample_msg += f"\n🆕 Found {len(new_samples)} NEW SAMPLES to test: {', '.join(new_samples)}"
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
    """Handle text messages (for confirm/cancel)"""
    user_id = update.effective_user.id
    text = update.message.text.lower().strip()
    
    if text == "confirm":
        if user_id not in user_sessions or not user_sessions[user_id].get("lineup"):
            await update.message.reply_text("❌ No lineup to confirm. Use /generate first.")
            return
        
        await update.message.reply_text("🚀 Updating Notion... This will take about 30-60 seconds.")
        
        lineup = user_sessions[user_id]["lineup"]
        due_date = user_sessions[user_id]["due_date"]
        
        success, failed, deleted = await create_notion_entries(lineup, due_date)
        
        result_msg = f"✅ *Done!*\n\n"
        if deleted > 0:
            result_msg += f"🗑️ Replaced: {deleted} old entries\n"
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
    user_sessions[user_id] = {"screenshots": [], "lineup": None}
    await update.message.reply_text("🗑️ Screenshots cleared. Ready for new ones!")


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


def main():
    """Start the bot"""
    # Log configuration on startup
    print(f"Starting TikTok Notion Bot...")
    print(f"Database ID: {NOTION_DATABASE_ID}")
    print(f"Notion API Key present: {bool(NOTION_API_KEY)}")
    print(f"Anthropic API Key present: {bool(ANTHROPIC_API_KEY)}")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
