"""Background scheduler for automatic email syncing."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from .database import SessionLocal
from .gmail_client import GmailClient
from .ai_classifier import AIClassifier
from .models import JobApplication, EmailProcessingLog
from .config import settings
import json


class EmailSyncScheduler:
    """Scheduler for background email synchronization."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.gmail_client = None
        self.ai_classifier = None
    
    def start(self):
        """Start the background scheduler."""
        # Add sync job
        self.scheduler.add_job(
            func=self.sync_job,
            trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
            id='email_sync_job',
            name='Sync job emails from Gmail',
            replace_existing=True
        )
        
        self.scheduler.start()
        print(f"✅ Email sync scheduler started (interval: {settings.sync_interval_minutes} minutes)")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("🛑 Email sync scheduler stopped")
    
    def sync_job(self):
        """Background job to sync emails."""
        print(f"\n🔄 Starting email sync at {datetime.utcnow().isoformat()}")
        
        try:
            # Initialize clients if not already
            if not self.gmail_client:
                self.gmail_client = GmailClient()
            if not self.ai_classifier:
                self.ai_classifier = AIClassifier()
            
            # Create database session
            db = SessionLocal()
            
            try:
                # Fetch emails
                emails = self.gmail_client.search_job_emails(
                    max_results=settings.max_emails_per_sync
                )
                
                processed_count = 0
                new_applications = 0
                updated_applications = 0
                
                for email in emails:
                    # Check if already processed
                    existing_log = db.query(EmailProcessingLog).filter(
                        EmailProcessingLog.gmail_message_id == email['message_id']
                    ).first()
                    
                    if existing_log:
                        continue
                    
                    # Classify email
                    classification = self.ai_classifier.classify_email(email)
                    
                    # Skip low-confidence OTHER classifications
                    if classification['status'] == 'OTHER' and classification['confidence'] < 0.5:
                        log = EmailProcessingLog(
                            gmail_message_id=email['message_id'],
                            classification='OTHER'
                        )
                        db.add(log)
                        processed_count += 1
                        continue
                    
                    # Check if job application exists
                    existing_app = db.query(JobApplication).filter(
                        JobApplication.gmail_thread_id == email['thread_id']
                    ).first()
                    
                    if existing_app:
                        # Update logic (same as main.py)
                        status_priority = {
                            'APPLIED': 1,
                            'INTERVIEW': 2,
                            'OFFER': 4,
                            'REJECTION': 3,
                            'GHOSTED': 0,
                            'OTHER': 0
                        }
                        
                        new_priority = status_priority.get(classification['status'], 0)
                        old_priority = status_priority.get(existing_app.status, 0)
                        
                        if new_priority > old_priority or email['date'] > existing_app.last_email_date:
                            existing_app.status = classification['status']
                            existing_app.confidence = classification['confidence']
                            existing_app.last_email_subject = email['subject']
                            existing_app.last_email_snippet = email['snippet']
                            existing_app.last_email_date = email['date']
                            existing_app.updated_at = datetime.utcnow()
                            
                            message_ids = json.loads(existing_app.gmail_message_ids or '[]')
                            if email['message_id'] not in message_ids:
                                message_ids.append(email['message_id'])
                                existing_app.gmail_message_ids = json.dumps(message_ids)
                            
                            updated_applications += 1
                    else:
                        # Create new application
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
                    
                    # Log as processed
                    log = EmailProcessingLog(
                        gmail_message_id=email['message_id'],
                        classification=classification['status']
                    )
                    db.add(log)
                    processed_count += 1
                
                db.commit()
                
                print(f"✅ Sync complete: {processed_count} processed, {new_applications} new, {updated_applications} updated")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Sync error: {e}")


# Global scheduler instance
scheduler = EmailSyncScheduler()
