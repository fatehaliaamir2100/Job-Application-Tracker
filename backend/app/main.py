"""Main FastAPI application."""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict
import json
from datetime import datetime, timedelta
import os

from .database import get_db, init_db
from .models import JobApplication, EmailProcessingLog
from .gmail_client import GmailClient
from .ai_classifier import AIClassifier
from .config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Job Application Tracker",
    description="AI-powered job application tracking using local Ollama models",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables."""
    init_db()
    print("✅ Database initialized")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Sync emails endpoint
@app.post("/api/sync")
async def sync_emails(
    background_tasks: BackgroundTasks,
    max_emails: int = 50,
    db: Session = Depends(get_db)
):
    """Sync emails from Gmail and classify them."""
    try:
        gmail_client = GmailClient()
        ai_classifier = AIClassifier()
        
        # Fetch emails
        emails = gmail_client.search_job_emails(max_results=max_emails)
        
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
            classification = ai_classifier.classify_email(email)
            
            # Skip if classification failed or is OTHER
            if classification['status'] == 'OTHER' and classification['confidence'] < 0.5:
                # Still log as processed
                log = EmailProcessingLog(
                    gmail_message_id=email['message_id'],
                    classification='OTHER'
                )
                db.add(log)
                processed_count += 1
                continue
            
            # Check if job application already exists (by thread_id)
            existing_app = db.query(JobApplication).filter(
                JobApplication.gmail_thread_id == email['thread_id']
            ).first()
            
            if existing_app:
                # Update existing application
                # Only update if new status is "more advanced" or more recent
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
                    
                    # Append message ID
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
        
        return {
            "success": True,
            "emails_fetched": len(emails),
            "emails_processed": processed_count,
            "new_applications": new_applications,
            "updated_applications": updated_applications
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get all job applications
@app.get("/api/applications")
async def get_applications(
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all job applications, optionally filtered by status."""
    query = db.query(JobApplication)
    
    if status:
        query = query.filter(JobApplication.status == status.upper())
    
    applications = query.order_by(JobApplication.updated_at.desc()).all()
    
    return {
        "total": len(applications),
        "applications": [
            {
                "id": app.id,
                "company": app.company,
                "role": app.role,
                "status": app.status,
                "confidence": app.confidence,
                "last_email_subject": app.last_email_subject,
                "last_email_snippet": app.last_email_snippet,
                "last_email_date": app.last_email_date.isoformat() if app.last_email_date else None,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
                "notes": app.notes
            }
            for app in applications
        ]
    }


# Get statistics
@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get application statistics."""
    total = db.query(JobApplication).count()
    
    statuses = {}
    for status in ['APPLIED', 'INTERVIEW', 'REJECTION', 'OFFER', 'GHOSTED', 'OTHER']:
        count = db.query(JobApplication).filter(
            JobApplication.status == status
        ).count()
        statuses[status.lower()] = count
    
    # Applications by date (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_apps = db.query(JobApplication).filter(
        JobApplication.created_at >= thirty_days_ago
    ).count()
    
    # Detect ghosted applications (no update in 14+ days, status = APPLIED)
    ghosted_threshold = datetime.utcnow() - timedelta(days=14)
    potentially_ghosted = db.query(JobApplication).filter(
        JobApplication.status == 'APPLIED',
        JobApplication.updated_at < ghosted_threshold
    ).count()
    
    return {
        "total_applications": total,
        "status_breakdown": statuses,
        "recent_applications": recent_apps,
        "potentially_ghosted": potentially_ghosted,
        "success_rate": round((statuses['interview'] + statuses['offer']) / total * 100, 2) if total > 0 else 0
    }


# Update application
@app.patch("/api/applications/{application_id}")
async def update_application(
    application_id: int,
    status: str = None,
    notes: str = None,
    db: Session = Depends(get_db)
):
    """Update a job application."""
    app = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if status:
        app.status = status.upper()
    
    if notes is not None:
        app.notes = notes
    
    app.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "application_id": application_id}


# Delete application
@app.delete("/api/applications/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    """Delete a job application."""
    app = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    db.delete(app)
    db.commit()
    
    return {"success": True, "message": "Application deleted"}


# Serve frontend
@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'index.html')
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Job Application Tracker API - Frontend not found"}


# Mount static files if frontend exists
frontend_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
