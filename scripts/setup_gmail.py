"""Setup Gmail API credentials."""
import os
import sys

def setup_gmail_credentials():
    """Guide user through Gmail API setup."""
    
    print("=" * 60)
    print("📧 Gmail API Setup")
    print("=" * 60)
    print()
    
    print("To use this app, you need to set up Gmail API access.")
    print()
    print("Follow these steps:")
    print()
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project (or select existing)")
    print("3. Enable Gmail API:")
    print("   - Go to 'APIs & Services' > 'Enable APIs and Services'")
    print("   - Search for 'Gmail API'")
    print("   - Click 'Enable'")
    print()
    print("4. Create OAuth 2.0 credentials:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
    print("   - Application type: 'Desktop app'")
    print("   - Name it whatever you want")
    print("   - Click 'Create'")
    print()
    print("5. Download credentials:")
    print("   - Click the download icon (⬇️) next to your OAuth 2.0 Client")
    print("   - Save the file as 'credentials.json'")
    print("   - Move it to this project's root directory")
    print()
    print("=" * 60)
    print()
    
    # Check if credentials exist
    if os.path.exists('credentials.json'):
        print("✅ Found credentials.json!")
        print()
        print("Run the app with:")
        print("  python -m backend.app.main")
        print()
        print("The first time you run it, you'll be asked to authorize")
        print("the app in your browser.")
    else:
        print("⚠️  credentials.json not found in current directory")
        print()
        print("After downloading credentials.json from Google Cloud,")
        print("place it in:")
        print(f"  {os.getcwd()}")
        
if __name__ == "__main__":
    setup_gmail_credentials()
