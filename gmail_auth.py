"""
Gmail OAuth2 Setup Script — Run this ONCE on your local PC.

Steps:
1. Go to https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable the Gmail API: APIs & Services > Library > Gmail API > Enable
4. Configure OAuth consent screen:
   - User type: External
   - App name: "TikTok Notion Bot"
   - User support email: thoard2021@gmail.com
   - Add test user: thoard2021@gmail.com
5. Create credentials:
   - APIs & Services > Credentials > Create Credentials > OAuth Client ID
   - Application type: Desktop app
   - Download JSON, save as 'credentials.json' in this folder
6. Run this script: python gmail_auth.py
7. Copy the output values to Render environment variables
"""

import json
import os

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency. Run: pip install google-auth-oauthlib")
    exit(1)

# Scopes needed for reading, sending, and labeling emails
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
]

def main():
    creds_file = os.path.join(os.path.dirname(__file__), 'credentials.json')
    
    if not os.path.exists(creds_file):
        print("ERROR: 'credentials.json' not found!")
        print("   Download it from Google Cloud Console > Credentials > OAuth Client ID")
        print("   Save it in this folder as 'credentials.json'")
        return
    
    print("Starting Gmail OAuth2 flow...")
    print("   A browser window will open. Log in with thoard2021@gmail.com\n")
    
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Read client ID and secret from credentials.json
    with open(creds_file, 'r') as f:
        client_config = json.load(f)
    
    # Handle both "installed" and "web" credential types
    config = client_config.get("installed") or client_config.get("web", {})
    
    client_id = config.get('client_id', 'CHECK credentials.json')
    client_secret = config.get('client_secret', 'CHECK credentials.json')
    refresh_token = creds.refresh_token
    
    output = (
        f"GMAIL_CLIENT_ID={client_id}\n"
        f"GMAIL_CLIENT_SECRET={client_secret}\n"
        f"GMAIL_REFRESH_TOKEN={refresh_token}\n"
    )
    
    # Save to file in case terminal closes
    output_file = os.path.join(os.path.dirname(__file__), 'gmail_creds_output.txt')
    with open(output_file, 'w') as f:
        f.write(output)
    
    print("\n" + "=" * 60)
    print("Authentication successful!")
    print("=" * 60)
    print("\nAdd these environment variables to Render:\n")
    print(output)
    print("=" * 60)
    print(f"Credentials also saved to: {output_file}")
    print("DELETE this file after copying the values!")
    print("=" * 60)


if __name__ == "__main__":
    main()
