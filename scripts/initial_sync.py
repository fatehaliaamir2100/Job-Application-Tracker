"""Initial email sync script."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database import init_db, SessionLocal
from backend.app.gmail_client import GmailClient
from backend.app.ai_classifier import AIClassifier
from backend.app.models import JobApplication, EmailProcessingLog
from datetime import datetime
import json


def initial_sync(max_emails=100):
    """Perform initial sync of job emails."""
    
    print("=" * 60)
    print("🚀 Initial Email Sync")
    print("=" * 60)
    print()
    
    # Initialize database
    print("📦 Initializing database...")
    init_db()
    print("✅ Database ready")
    print()
    
    # Initialize clients
    print("🔌 Connecting to Gmail...")
    try:
        gmail_client = GmailClient()
        print("✅ Gmail connected")
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        print()
        print("Run: python scripts/setup_gmail.py")
        return
    
    print()
    print("🤖 Initializing AI classifier (Ollama)...")
    try:
        ai_classifier = AIClassifier()
        print("✅ AI classifier ready")
    except Exception as e:
        print(f"❌ AI classifier failed: {e}")
        print()
        print("Make sure Ollama is running:")
        print("  ollama serve")
        return
    
    print()
    print(f"📧 Fetching up to {max_emails} job-related emails...")
    
    try:
        emails = gmail_client.search_job_emails(max_results=max_emails)
        print(f"✅ Found {len(emails)} emails")
    except Exception as e:
        print(f"❌ Email fetch failed: {e}")
        return
    
    print()
    print("🔄 Processing emails...")
    print()
    
    db = SessionLocal()
    processed_count = 0
    new_applications = 0
    
    try:
        for i, email in enumerate(emails, 1):
            print(f"[{i}/{len(emails)}] Processing: {email['subject'][:50]}...")
            
            # Check if already processed
            existing_log = db.query(EmailProcessingLog).filter(
                EmailProcessingLog.gmail_message_id == email['message_id']
            ).first()
            
            if existing_log:
                print("  ⏭️  Already processed, skipping")
                continue
            
            # Classify
            classification = ai_classifier.classify_email(email)
            print(f"  ✓ Classified as: {classification['status']} (confidence: {classification['confidence']:.2f})")
            
            # Skip low-confidence OTHER
            if classification['status'] == 'OTHER' and classification['confidence'] < 0.5:
                log = EmailProcessingLog(
                    gmail_message_id=email['message_id'],
                    classification='OTHER'
                )
                db.add(log)
                processed_count += 1
                continue
            
            # Check if application exists
            existing_app = db.query(JobApplication).filter(
                JobApplication.gmail_thread_id == email['thread_id']
            ).first()
            
            if existing_app:
                print(f"  📝 Updating existing application for {existing_app.company}")
            else:
                # Create new
                new_app = JobApplication(
                    company=classification['company'],
                    role=classification['role'],
                    status=classification['status'],
                    confidence=classification['confidence'],
                    gmail_thread_id=email['thread_id'],
                    gmail_message_ids=json.dumps([email['message_id']]),
                    last_email_subject=email['subject'],
                    last_email_snippet=email['snippet'],
                    last_email_date=email['date']
                )
                db.add(new_app)
                new_applications += 1
                print(f"  ✨ Created new application: {classification['company']} - {classification['role']}")
            
            # Log as processed
            log = EmailProcessingLog(
                gmail_message_id=email['message_id'],
                classification=classification['status']
            )
            db.add(log)
            processed_count += 1
        
        db.commit()
        
        print()
        print("=" * 60)
        print("✅ Initial sync complete!")
        print("=" * 60)
        print(f"📊 Processed: {processed_count} emails")
        print(f"✨ New applications: {new_applications}")
        print()
        print("Start the app:")
        print("  python -m backend.app.main")
        print()
        print("Or with auto-sync:")
        print("  python run.py")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Initial email sync')
    parser.add_argument('--max-emails', type=int, default=100,
                       help='Maximum number of emails to process')
    
    args = parser.parse_args()
    initial_sync(max_emails=args.max_emails)
