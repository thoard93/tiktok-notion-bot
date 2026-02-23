"""
Gmail Outreach Auto-Responder Module

Scans thoard2021@gmail.com for TikTok Shop brand outreach emails,
classifies them with Claude AI, sends Telegram notifications for approval,
auto-replies with retainer offers, and tracks deals in Notion.
"""

import os
import json
import base64
import asyncio
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import anthropic

# Gmail API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configuration
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN")
OUTREACH_NOTION_DB_ID = os.environ.get("OUTREACH_NOTION_DB_ID")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Default retainer settings (can be changed with /setrate)
DEFAULT_RETAINER_VIDEOS = 30
DEFAULT_RETAINER_RATE = 500

# Auto-approve threshold (confidence >= this AND not suspicious = auto-reply)
# Set to None or 0 to disable auto-approval
AUTO_APPROVE_THRESHOLD = 0.70

# Auto-skip threshold (confidence <= this = silently skip, no notification)
# Set to None or 0 to disable auto-skipping
AUTO_SKIP_THRESHOLD = 0.40

# Label name for processed emails
PROCESSED_LABEL = "Outreach-Processed"

# Store pending outreach for Telegram approval (message_id -> outreach_data)
pending_outreach = {}


# =============================================================================
# Gmail Client
# =============================================================================

class GmailClient:
    """Handles Gmail API authentication, reading, replying, and labeling."""
    
    def __init__(self):
        self.service = None
        self.processed_label_id = None
    
    def authenticate(self):
        """Authenticate using OAuth2 refresh token (no browser needed)."""
        if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
            print("⚠️ Gmail credentials not configured. Outreach scanning disabled.")
            return False
        
        try:
            creds = Credentials(
                token=None,
                refresh_token=GMAIL_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GMAIL_CLIENT_ID,
                client_secret=GMAIL_CLIENT_SECRET,
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.modify',
                    'https://www.googleapis.com/auth/gmail.labels',
                ]
            )
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail API authenticated successfully")
            return True
        except Exception as e:
            print(f"❌ Gmail authentication failed: {e}")
            return False
    
    def _ensure_label(self):
        """Create the 'Outreach-Processed' label if it doesn't exist."""
        if self.processed_label_id:
            return self.processed_label_id
        
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            for label in labels:
                if label['name'] == PROCESSED_LABEL:
                    self.processed_label_id = label['id']
                    return self.processed_label_id
            
            # Create the label
            label_body = {
                'name': PROCESSED_LABEL,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            created = self.service.users().labels().create(
                userId='me', body=label_body
            ).execute()
            self.processed_label_id = created['id']
            print(f"✅ Created Gmail label: {PROCESSED_LABEL}")
            return self.processed_label_id
        except Exception as e:
            print(f"Error creating label: {e}")
            return None
    
    def fetch_new_emails(self, max_results=10):
        """Fetch unread emails that look like outreach and haven't been processed."""
        if not self.service:
            return []
        
        try:
            # Search for unread emails from the last 14 days, excluding already-processed ones
            query = f"is:unread -label:{PROCESSED_LABEL} newer_than:14d"
            
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages  # List of {'id': ..., 'threadId': ...}
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def get_email_content(self, msg_id):
        """Extract full email content including sender, subject, body, and headers."""
        if not self.service:
            return None
        
        try:
            msg = self.service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            
            headers = msg.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract body text
            body = self._extract_body(msg.get('payload', {}))
            
            return {
                'id': msg_id,
                'thread_id': msg.get('threadId'),
                'subject': header_dict.get('subject', '(No Subject)'),
                'from': header_dict.get('from', ''),
                'to': header_dict.get('to', ''),
                'date': header_dict.get('date', ''),
                'message_id': header_dict.get('message-id', ''),
                'in_reply_to': header_dict.get('in-reply-to', ''),
                'body': body,
                'snippet': msg.get('snippet', ''),
            }
        except Exception as e:
            print(f"Error getting email {msg_id}: {e}")
            return None
    
    def _extract_body(self, payload):
        """Recursively extract text body from email payload."""
        body_text = ""
        
        if payload.get('mimeType') == 'text/plain':
            data = payload.get('body', {}).get('data', '')
            if data:
                body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        elif payload.get('mimeType', '').startswith('multipart/'):
            for part in payload.get('parts', []):
                body_text += self._extract_body(part)
        elif payload.get('mimeType') == 'text/html' and not body_text:
            # Fallback to HTML if no plain text
            data = payload.get('body', {}).get('data', '')
            if data:
                html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                # Basic HTML stripping
                import re
                body_text = re.sub(r'<[^>]+>', ' ', html)
                body_text = re.sub(r'\s+', ' ', body_text).strip()
        
        return body_text
    
    def send_reply(self, original_email, reply_text):
        """Send a threaded reply to an email."""
        if not self.service:
            return False
        
        try:
            # Parse sender email address
            from_addr = original_email['from']
            # Extract just the email if it's in "Name <email>" format
            if '<' in from_addr:
                reply_to = from_addr.split('<')[1].rstrip('>')
            else:
                reply_to = from_addr
            
            # Build the reply message
            message = MIMEMultipart()
            message['to'] = reply_to
            message['subject'] = f"Re: {original_email['subject']}"
            message['In-Reply-To'] = original_email['message_id']
            message['References'] = original_email['message_id']
            
            message.attach(MIMEText(reply_text, 'plain'))
            
            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw,
                    'threadId': original_email['thread_id']
                }
            ).execute()
            
            print(f"✅ Reply sent to {reply_to}")
            return True
        except Exception as e:
            print(f"❌ Error sending reply: {e}")
            return False
    
    def label_as_processed(self, msg_id):
        """Add the 'Outreach-Processed' label and mark as read."""
        if not self.service:
            return
        
        label_id = self._ensure_label()
        if not label_id:
            return
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={
                    'addLabelIds': [label_id],
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
        except Exception as e:
            print(f"Error labeling email {msg_id}: {e}")
    
    def check_if_reply_to_us(self, thread_id):
        """Check if we sent a retainer offer in this thread (via the bot).
        Only returns True if our sent message contains retainer offer keywords,
        not just any random reply we sent manually."""
        if not self.service:
            return False
        
        try:
            thread = self.service.users().threads().get(
                userId='me', id=thread_id, format='full'
            ).execute()
            
            messages = thread.get('messages', [])
            
            # Get our email address
            profile = self.service.users().getProfile(userId='me').execute()
            our_email = profile.get('emailAddress', '').lower()
            
            # Keywords that only appear in our bot-generated retainer offers
            offer_keywords = ['retainer package', 'bof', 'bottom-of-funnel', 'flat fee']
            
            for msg in messages:
                headers = msg.get('payload', {}).get('headers', [])
                from_header = ''
                for h in headers:
                    if h['name'].lower() == 'from':
                        from_header = h['value'].lower()
                        break
                
                # Only check messages sent by us
                if our_email not in from_header:
                    continue
                
                # Check if the body contains our retainer offer keywords
                body = self._extract_body(msg.get('payload', {}))
                body_lower = body.lower()
                
                if any(kw in body_lower for kw in offer_keywords):
                    return True
            
            return False
        except Exception as e:
            print(f"Error checking thread {thread_id}: {e}")
            return False


# =============================================================================
# AI Classifier
# =============================================================================

class OutreachClassifier:
    """Uses Claude AI to classify emails as outreach, extract info, and detect scams."""
    
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    
    async def classify_email(self, subject, body, sender):
        """Classify an email and extract brand information."""
        
        # Truncate body to avoid excessive token usage
        body_truncated = body[:3000] if body else "(empty)"
        
        prompt = f"""Analyze this email and determine if it's a genuine TikTok Shop brand/seller outreach looking for content creator collaboration.

FROM: {sender}
SUBJECT: {subject}

BODY:
{body_truncated}

Respond with ONLY a JSON object (no other text):
{{
    "is_outreach": true/false,
    "is_suspicious": true/false,
    "brand_name": "extracted brand name or null",
    "product_type": "what they sell (e.g. skincare, supplements, kitchen) or null",
    "contact_name": "person's name who sent it or null",
    "offer_summary": "1-2 sentence summary of what they want or null",
    "confidence": 0.0-1.0,
    "suspicious_reasons": ["list of red flags if suspicious, else empty"]
}}

Classification rules:
- is_outreach = true: Email is from a brand/seller wanting to collaborate on TikTok Shop content
- is_outreach = false: Newsletter, receipt, notification, personal email, promo, spam
- is_suspicious = true: No real brand name, asks for personal/financial info upfront, crypto/NFT, urgency pressure, too-good-to-be-true offers, poor grammar suggesting scam
- confidence: How confident you are this is legitimate outreach (0.0 = definitely not, 1.0 = definitely yes)

Only return the JSON object, nothing else."""

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            
            # Clean markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            return json.loads(result_text.strip())
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing classification: {e}")
            return {
                "is_outreach": False,
                "is_suspicious": False,
                "brand_name": None,
                "product_type": None,
                "contact_name": None,
                "offer_summary": None,
                "confidence": 0.0,
                "suspicious_reasons": []
            }
        except Exception as e:
            print(f"Error classifying email: {e}")
            return None


# =============================================================================
# Outreach Responder
# =============================================================================

class OutreachResponder:
    """Generates and sends retainer offer replies."""
    
    def __init__(self, gmail_client):
        self.gmail = gmail_client
        self.default_videos = DEFAULT_RETAINER_VIDEOS
        self.default_rate = DEFAULT_RETAINER_RATE
    
    def generate_reply(self, classification, custom_rate=None):
        """Generate the retainer offer reply text."""
        contact = classification.get("contact_name") or "there"
        brand = classification.get("brand_name") or "your brand"
        rate = custom_rate or self.default_rate
        videos = self.default_videos
        
        reply = (
            f"Hi {contact},\n\n"
            f"Thanks for reaching out! I'd love to work with {brand}.\n\n"
            f"Just so you know, I specialize in BOF (bottom-of-funnel) content \u2014 "
            f"discount-based TikTok Shop videos that drive direct conversions rather than "
            f"top-of-funnel brand awareness. My videos are built around compelling offers, "
            f"promo codes, and urgency to get viewers to buy.\n\n"
            f"I currently offer a retainer package: {videos} high-quality BOF TikTok Shop videos "
            f"featuring your product for a flat fee of ${rate}. All videos are optimized for "
            f"conversions and posted across my TikTok accounts.\n\n"
            f"If that sounds like a fit for your brand, let me know and I'll send over more details!\n\n"
            f"Best,\n"
            f"Thomas"
        )
        return reply
    
    def send_retainer_offer(self, original_email, classification, custom_rate=None):
        """Send the retainer offer reply."""
        reply_text = self.generate_reply(classification, custom_rate)
        return self.gmail.send_reply(original_email, reply_text)


# =============================================================================
# Notion Deal Tracker
# =============================================================================

class OutreachNotionTracker:
    """Tracks outreach deals in a dedicated Notion database."""
    
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def create_deal(self, classification, email_data, status="New", retainer_amount=None):
        """Create a deal entry in the Outreach Notion database."""
        if not OUTREACH_NOTION_DB_ID:
            print("⚠️ OUTREACH_NOTION_DB_ID not set, skipping Notion tracking")
            return False
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                "parent": {"database_id": OUTREACH_NOTION_DB_ID},
                "properties": {
                    "Brand Name": {
                        "title": [{"text": {"content": classification.get("brand_name") or "Unknown Brand"}}]
                    },
                    "Contact Email": {
                        "email": email_data.get("from", "").split('<')[-1].rstrip('>') if '<' in email_data.get("from", "") else email_data.get("from", "")
                    },
                    "Contact Name": {
                        "rich_text": [{"text": {"content": classification.get("contact_name") or "Unknown"}}]
                    },
                    "Product Type": {
                        "select": {"name": classification.get("product_type") or "Other"}
                    },
                    "Offer Summary": {
                        "rich_text": [{"text": {"content": (classification.get("offer_summary") or "No summary")[:2000]}}]
                    },
                    "Status": {
                        "select": {"name": status}
                    },
                    "Date Received": {
                        "date": {"start": datetime.now().strftime("%Y-%m-%d")}
                    },
                    "Suspicious": {
                        "checkbox": classification.get("is_suspicious", False)
                    }
                }
            }
            
            # Add optional fields
            if retainer_amount:
                data["properties"]["Retainer Amount"] = {
                    "number": retainer_amount
                }
            
            if status == "Replied":
                data["properties"]["Date Replied"] = {
                    "date": {"start": datetime.now().strftime("%Y-%m-%d")}
                }
            
            response = await client.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"Error creating Notion deal: {response.status_code} - {response.text}")
                return False
            
            print(f"✅ Notion deal created for {classification.get('brand_name')}")
            return True
    
    async def get_stats(self):
        """Get outreach statistics."""
        if not OUTREACH_NOTION_DB_ID:
            return None
        
        stats = {"total": 0, "replied": 0, "declined": 0, "deals_closed": 0, "suspicious": 0}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            has_more = True
            start_cursor = None
            
            while has_more:
                body = {"page_size": 100}
                if start_cursor:
                    body["start_cursor"] = start_cursor
                
                response = await client.post(
                    f"{self.base_url}/databases/{OUTREACH_NOTION_DB_ID}/query",
                    headers=self.headers,
                    json=body
                )
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                for page in data.get("results", []):
                    stats["total"] += 1
                    props = page.get("properties", {})
                    
                    status = props.get("Status", {}).get("select", {})
                    status_name = status.get("name", "") if status else ""
                    
                    if status_name == "Replied":
                        stats["replied"] += 1
                    elif status_name == "Declined":
                        stats["declined"] += 1
                    elif status_name == "Deal Closed":
                        stats["deals_closed"] += 1
                    
                    suspicious = props.get("Suspicious", {}).get("checkbox", False)
                    if suspicious:
                        stats["suspicious"] += 1
                
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
        
        return stats


# =============================================================================
# Outreach Scanner (ties everything together)
# =============================================================================

class OutreachScanner:
    """Main scanner that coordinates Gmail reading, AI classification, and notifications."""
    
    def __init__(self):
        self.gmail = GmailClient()
        self.classifier = OutreachClassifier()
        self.responder = OutreachResponder(self.gmail)
        self.tracker = OutreachNotionTracker()
        self.is_ready = False
    
    def initialize(self):
        """Set up Gmail connection."""
        self.is_ready = self.gmail.authenticate()
        return self.is_ready
    
    async def scan_for_outreach(self):
        """Scan inbox for new outreach emails and classify them.
        Returns list of classified outreach emails."""
        if not self.is_ready:
            print("⚠️ Outreach scanner not initialized")
            return []
        
        print(f"📧 Scanning inbox for outreach emails...")
        messages = self.gmail.fetch_new_emails(max_results=10)
        
        if not messages:
            print("No new emails found")
            return []
        
        print(f"Found {len(messages)} unread emails, classifying...")
        outreach_emails = []
        followup_emails = []
        
        for msg_info in messages:
            msg_id = msg_info['id']
            thread_id = msg_info.get('threadId', '')
            
            # Get full email content
            email_data = self.gmail.get_email_content(msg_id)
            if not email_data:
                continue
            
            # Skip system/daemon emails (bounce-backs, delivery failures, etc.)
            sender_lower = email_data.get('from', '').lower()
            system_senders = ['mailer-daemon', 'postmaster', 'noreply', 'no-reply', 'notifications@']
            if any(s in sender_lower for s in system_senders):
                self.gmail.label_as_processed(msg_id)
                print(f"  Skipped system email: {email_data['from'][:40]}")
                continue
            
            # Check if this is a reply to a thread we already sent a retainer offer in
            if self.gmail.check_if_reply_to_us(thread_id):
                # This is a brand following up on our retainer offer!
                self.gmail.label_as_processed(msg_id)
                followup_emails.append(email_data)
                print(f"  Reply detected: {email_data['from'][:40]} re: {email_data['subject'][:40]}")
                continue
            
            # Classify with Claude
            classification = await self.classifier.classify_email(
                subject=email_data['subject'],
                body=email_data['body'],
                sender=email_data['from']
            )
            
            if classification is None:
                continue
            
            # Label as processed regardless of classification
            self.gmail.label_as_processed(msg_id)
            
            # Only report actual outreach
            if classification.get('is_outreach', False):
                outreach_entry = {
                    'email': email_data,
                    'classification': classification,
                    'msg_id': msg_id
                }
                outreach_emails.append(outreach_entry)
                print(f"  Outreach from: {classification.get('brand_name', 'Unknown')} "
                      f"(confidence: {classification.get('confidence', 0):.0%})")
            else:
                print(f"  Skipped: {email_data['subject'][:50]}...")
            
            # Small delay between API calls
            await asyncio.sleep(0.5)
        
        print(f"Found {len(outreach_emails)} outreach emails, {len(followup_emails)} follow-ups")
        return outreach_emails, followup_emails
    
    async def approve_and_reply(self, outreach_id, custom_rate=None):
        """Approve an outreach email and send the retainer offer."""
        if outreach_id not in pending_outreach:
            return False, "Outreach not found or already processed"
        
        entry = pending_outreach[outreach_id]
        email_data = entry['email']
        classification = entry['classification']
        rate = custom_rate or self.responder.default_rate
        
        # Send reply
        success = self.responder.send_retainer_offer(email_data, classification, custom_rate=rate)
        
        if success:
            # Track in Notion
            await self.tracker.create_deal(
                classification=classification,
                email_data=email_data,
                status="Replied",
                retainer_amount=rate
            )
            
            # Remove from pending
            del pending_outreach[outreach_id]
            brand = classification.get('brand_name', 'Unknown')
            return True, f"Reply sent to {brand} with ${rate} offer"
        else:
            return False, "Failed to send reply"
    
    async def skip_outreach(self, outreach_id):
        """Skip/decline an outreach email."""
        if outreach_id not in pending_outreach:
            return False, "Outreach not found"
        
        entry = pending_outreach[outreach_id]
        classification = entry['classification']
        email_data = entry['email']
        
        # Track as declined in Notion
        await self.tracker.create_deal(
            classification=classification,
            email_data=email_data,
            status="Declined"
        )
        
        del pending_outreach[outreach_id]
        return True, f"Skipped {classification.get('brand_name', 'Unknown')}"
    
    async def mark_scam(self, outreach_id):
        """Mark an outreach email as a scam."""
        if outreach_id not in pending_outreach:
            return False, "Outreach not found"
        
        entry = pending_outreach[outreach_id]
        classification = entry['classification']
        classification['is_suspicious'] = True
        email_data = entry['email']
        
        # Track as scam in Notion
        await self.tracker.create_deal(
            classification=classification,
            email_data=email_data,
            status="Scam"
        )
        
        del pending_outreach[outreach_id]
        return True, f"Marked {classification.get('brand_name', 'Unknown')} as scam"


# =============================================================================
# Background Scheduler
# =============================================================================

async def outreach_scan_loop(scanner, bot, chat_id, interval_minutes=30):
    """Background loop that scans for outreach every N minutes.
    High-confidence, non-suspicious emails are auto-approved and replied to."""
    print(f"Outreach scanner starting (every {interval_minutes} min)")
    
    while True:
        try:
            outreach_emails, followup_emails = await scanner.scan_for_outreach()
            
            # Handle brand follow-up replies (they replied to our retainer offer!)
            for followup in followup_emails:
                await send_followup_notification(bot, chat_id, followup)
            
            for entry in outreach_emails:
                classification = entry['classification']
                confidence = classification.get('confidence', 0)
                is_suspicious = classification.get('is_suspicious', False)
                
                # Tier 1: Low confidence — silently skip (no notification)
                skip_threshold = AUTO_SKIP_THRESHOLD
                if skip_threshold and confidence <= skip_threshold:
                    await auto_skip_outreach(scanner, entry)
                # Tier 2: High confidence + not suspicious — auto-approve & reply
                elif AUTO_APPROVE_THRESHOLD and confidence >= AUTO_APPROVE_THRESHOLD and not is_suspicious:
                    await auto_approve_outreach(scanner, bot, chat_id, entry)
                # Tier 3: Middle ground — manual approval via Telegram
                else:
                    await send_outreach_notification(bot, chat_id, entry)
            
        except Exception as e:
            print(f"Error in outreach scan loop: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait for next scan
        await asyncio.sleep(interval_minutes * 60)


async def auto_skip_outreach(scanner, outreach_entry):
    """Silently skip a low-confidence outreach email. No Telegram notification."""
    classification = outreach_entry['classification']
    email_data = outreach_entry['email']
    brand = classification.get('brand_name') or 'Unknown'
    confidence = classification.get('confidence', 0)
    is_suspicious = classification.get('is_suspicious', False)
    
    # Log as Scam if suspicious, otherwise Declined
    status = "Scam" if is_suspicious else "Declined"
    
    await scanner.tracker.create_deal(
        classification=classification,
        email_data=email_data,
        status=status
    )
    
    print(f"  Auto-skipped: {brand} (confidence: {confidence:.0%}, status: {status})")


async def auto_approve_outreach(scanner, bot, chat_id, outreach_entry):
    """Auto-approve and reply to a high-confidence outreach email, then notify user."""
    classification = outreach_entry['classification']
    email_data = outreach_entry['email']
    brand = classification.get('brand_name') or 'Unknown Brand'
    confidence = classification.get('confidence', 0)
    rate = scanner.responder.default_rate
    
    # Send the retainer offer reply automatically
    success = scanner.responder.send_retainer_offer(email_data, classification)
    
    if success:
        # Track in Notion as Replied
        await scanner.tracker.create_deal(
            classification=classification,
            email_data=email_data,
            status="Replied",
            retainer_amount=rate
        )
        
        # Send informational notification (no buttons — already handled)
        contact = classification.get('contact_name') or 'Unknown'
        product = classification.get('product_type') or 'Unknown'
        sender = email_data.get('from', '')
        summary = classification.get('offer_summary') or email_data.get('snippet', '')[:200]
        
        msg = (
            f"\u2705 *Auto-Approved & Replied*\n\n"
            f"\U0001f3f7\ufe0f *Brand:* {brand} ({product})\n"
            f"\U0001f464 *Contact:* {contact}\n"
            f"\U0001f4e9 *From:* {sender}\n\n"
            f"\U0001f4dd *Summary:* {summary}\n\n"
            f"\U0001f4b0 Sent ${rate} retainer offer ({scanner.responder.default_videos} videos)\n"
            f"\u2705 Confidence: {confidence:.0%} legitimate"
        )
        
        try:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error sending auto-approve notification: {e}")
    else:
        # If reply failed, fall back to manual approval
        print(f"Auto-reply failed for {brand}, falling back to manual approval")
        await send_outreach_notification(bot, chat_id, outreach_entry)


async def send_followup_notification(bot, chat_id, email_data):
    """Notify user when a brand replies to our retainer offer — this is a hot lead!"""
    sender = email_data.get('from', 'Unknown')
    subject = email_data.get('subject', '(No Subject)')
    snippet = email_data.get('snippet', '')[:300]
    date = email_data.get('date', 'Unknown')
    
    msg = (
        f"\U0001f525 *Brand Replied to Your Offer!*\n\n"
        f"\U0001f4e9 *From:* {sender}\n"
        f"\U0001f4cc *Subject:* {subject}\n"
        f"\U0001f4c5 *Date:* {date}\n\n"
        f"\U0001f4ac *Their Reply:*\n{snippet}\n\n"
        f"\u2757 Check your Gmail to respond!"
    )
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Error sending followup notification: {e}")


async def send_outreach_notification(bot, chat_id, outreach_entry):
    """Send a Telegram notification with inline approval buttons (for lower-confidence emails)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    classification = outreach_entry['classification']
    email_data = outreach_entry['email']
    
    # Generate a unique ID for this outreach
    outreach_id = email_data['id'][:12]
    
    # Store in pending
    pending_outreach[outreach_id] = outreach_entry
    
    # Build notification message
    brand = classification.get('brand_name') or 'Unknown Brand'
    contact = classification.get('contact_name') or 'Unknown'
    product = classification.get('product_type') or 'Unknown'
    sender = email_data.get('from', '')
    confidence = classification.get('confidence', 0)
    summary = classification.get('offer_summary') or email_data.get('snippet', '')[:200]
    suspicious = classification.get('is_suspicious', False)
    sus_reasons = classification.get('suspicious_reasons', [])
    
    msg = (
        f"📧 *New Brand Outreach Detected!*\n\n"
        f"🏷️ *Brand:* {brand} ({product})\n"
        f"👤 *Contact:* {contact}\n"
        f"📩 *From:* {sender}\n"
        f"📅 *Date:* {email_data.get('date', 'Unknown')}\n\n"
        f"📝 *Summary:* {summary}\n\n"
    )
    
    if suspicious:
        msg += f"🚨 *SUSPICIOUS* — {', '.join(sus_reasons)}\n\n"
    
    msg += f"{'⚠️' if confidence < 0.7 else '✅'} Confidence: {confidence:.0%} legitimate"
    
    # Build inline keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve ($" + str(DEFAULT_RETAINER_RATE) + ")", 
                               callback_data=f"outreach_approve_{outreach_id}"),
            InlineKeyboardButton("💰 Custom Rate", 
                               callback_data=f"outreach_custom_{outreach_id}"),
        ],
        [
            InlineKeyboardButton("❌ Skip", 
                               callback_data=f"outreach_skip_{outreach_id}"),
            InlineKeyboardButton("🚫 Mark Scam", 
                               callback_data=f"outreach_scam_{outreach_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error sending outreach notification: {e}")
