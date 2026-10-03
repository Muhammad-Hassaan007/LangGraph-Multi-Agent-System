"""
Google Calendar One-Time OAuth Authorization Script.
Run this script in terminal to log in with your Google account.
It will open a browser window and save the authorization token to 'token.json'.
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events"
]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(base_dir, "credentials.json")
    token_path = os.path.join(base_dir, "token.json")

    if not os.path.exists(creds_path):
        print(f"❌ Error: {creds_path} not found.")
        sys.exit(1)

    print("🔐 Starting Google Calendar OAuth Authorization...")
    print("🌐 A browser window will now open asking you to sign in with your Google account.")
    print("👉 If you see 'Google hasn't verified this app', click 'Advanced' -> 'Go to smit-restaurant-ai (unsafe)' -> 'Allow'.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

        print(f"\n🎉 SUCCESS! token.json has been created at: {token_path}")
        print("✅ Google Calendar is now fully connected to the Multi-Agent System!")
    except Exception as e:
        print(f"\n❌ Authorization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
