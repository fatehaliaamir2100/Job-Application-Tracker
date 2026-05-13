"""Main FastAPI application."""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict
import json
from datetime import datetime, timedelta
import os
import shutil

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from .database import get_db, init_db
from .models import JobApplication, EmailProcessingLog
from .gmail_client import GmailClient
from .ai_classifier import AIClassifier
from .config import settings
from .scheduler import scheduler

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
    """Initialize database tables and start background scheduler."""
    init_db()
    print("✅ Database initialized")
    token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
    if os.path.exists(token_path):
        try:
            scheduler.start()
        except Exception as e:
            print(f"⚠️ Scheduler failed to start: {e}")
    else:
        print("⏩ Scheduler skipped — Gmail not connected yet")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the background scheduler on shutdown."""
    try:
        scheduler.stop()
    except Exception:
        pass


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Setup status check
@app.get("/api/setup-status")
async def check_setup_status():
    """Check if Gmail credentials are configured."""
    credentials_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
    token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
    
    has_credentials = os.path.exists(credentials_path)
    has_token = os.path.exists(token_path)
    
    return {
        "is_setup": has_credentials and has_token,
        "has_credentials": has_credentials,
        "has_token": has_token,
        "needs_onboarding": not (has_credentials and has_token)
    }


# Get Gmail OAuth URL
@app.get("/api/auth/gmail/url")
async def get_gmail_auth_url():
    """Generate Gmail OAuth authorization URL with manual PKCE."""
    import hashlib
    import base64
    import secrets
    import urllib.parse

    credentials_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')

    if not os.path.exists(credentials_path):
        raise HTTPException(status_code=400, detail="credentials.json not found. Please upload it first.")

    try:
        with open(credentials_path, 'r') as f:
            client_config = json.load(f)

        client_info = client_config.get('installed') or client_config.get('web')
        if not client_info:
            raise HTTPException(status_code=400, detail="Invalid credentials file format")

        client_id  = client_info['client_id']
        client_secret = client_info['client_secret']
        auth_uri   = client_info['auth_uri']
        token_uri  = client_info['token_uri']
        redirect_uri = 'http://localhost:8000/api/auth/gmail/callback'

        # --- Generate PKCE pair manually ---
        raw = secrets.token_bytes(32)
        code_verifier = base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

        state = secrets.token_urlsafe(24)

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/gmail.readonly',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        authorization_url = auth_uri + '?' + urllib.parse.urlencode(params)

        # Persist EVERYTHING needed for the callback
        flow_data = {
            'state': state,
            'code_verifier': code_verifier,
            'client_id': client_id,
            'client_secret': client_secret,
            'token_uri': token_uri,
            'redirect_uri': redirect_uri,
        }
        flow_path = os.path.join(os.path.dirname(__file__), '..', '..', f'flow_{state}.json')
        with open(flow_path, 'w') as f:
            json.dump(flow_data, f)

        return {"auth_url": authorization_url, "state": state}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


# Handle Gmail OAuth callback
@app.get("/api/auth/gmail/callback")
async def gmail_auth_callback(code: str, state: str = None, scope: str = None, error: str = None):
    """Handle OAuth callback — exchange code + code_verifier for tokens."""
    import urllib.request
    import urllib.parse
    from google.oauth2.credentials import Credentials
    from fastapi.responses import HTMLResponse

    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
    flow_path  = os.path.join(os.path.dirname(__file__), '..', '..', f'flow_{state}.json')

    try:
        if not os.path.exists(flow_path):
            raise HTTPException(status_code=400, detail="Invalid or expired session. Please try again.")

        with open(flow_path, 'r') as f:
            flow_data = json.load(f)

        # Exchange code for tokens, sending code_verifier for PKCE
        post_data = urllib.parse.urlencode({
            'code': code,
            'client_id': flow_data['client_id'],
            'client_secret': flow_data['client_secret'],
            'redirect_uri': flow_data['redirect_uri'],
            'grant_type': 'authorization_code',
            'code_verifier': flow_data['code_verifier'],  # PKCE proof
        }).encode('utf-8')

        req = urllib.request.Request(
            flow_data['token_uri'],
            data=post_data,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urllib.request.urlopen(req) as resp:
            token = json.loads(resp.read().decode('utf-8'))

        # Save as Google Credentials JSON
        creds = Credentials(
            token=token['access_token'],
            refresh_token=token.get('refresh_token'),
            token_uri=flow_data['token_uri'],
            client_id=flow_data['client_id'],
            client_secret=flow_data['client_secret'],
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

        # Clean up
        os.remove(flow_path)
        
        # Return success page that redirects to dashboard
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gmail Connected</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d0d0d;
            color: #ebebeb;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card {
            background: #141414;
            border: 1px solid #242424;
            border-radius: 12px;
            padding: 48px 52px;
            text-align: center;
            width: 100%;
            max-width: 380px;
        }
        .icon {
            font-size: 2rem;
            margin-bottom: 20px;
            animation: fadeUp 0.3s ease-out;
        }
        h1 {
            font-size: 1.25rem;
            font-weight: 600;
            color: #fff;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }
        p {
            font-size: 0.8rem;
            color: #787878;
        }
        .bar {
            height: 2px;
            background: #1c1c1c;
            border-radius: 2px;
            margin-top: 28px;
            overflow: hidden;
        }
        .bar-fill {
            height: 100%;
            background: #fff;
            border-radius: 2px;
            animation: progress 2s linear forwards;
        }
        @keyframes progress {
            from { width: 0%; }
            to   { width: 100%; }
        }
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(6px); }
            to   { opacity: 1; transform: translateY(0); }
        }
    </style>
    <script>setTimeout(() => { window.location.href = '/'; }, 2000);</script>
</head>
<body>
    <div class="card">
        <div class="icon">&#10003;</div>
        <h1>Gmail connected</h1>
        <p>Redirecting to dashboard...</p>
        <div class="bar"><div class="bar-fill"></div></div>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


# Upload credentials file
@app.post("/api/upload-credentials")
async def upload_credentials(file: UploadFile = File(...)):
    """Upload credentials.json file."""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    try:
        # Read and validate JSON
        contents = await file.read()
        json_data = json.loads(contents)
        
        # Basic validation
        if 'installed' not in json_data and 'web' not in json_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid credentials file format. Please download OAuth 2.0 Client ID credentials from Google Cloud Console."
            )
        
        # Save to project root
        credentials_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
        with open(credentials_path, 'wb') as f:
            f.write(contents)
        
        return {"success": True, "message": "Credentials uploaded successfully"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload credentials: {str(e)}")


# Sync emails endpoint
@app.post("/api/sync")
async def sync_emails(
    background_tasks: BackgroundTasks,
    max_emails: int = 10,
    db: Session = Depends(get_db)
):
    """Sync emails from Gmail and classify them."""
    try:
        print("[SYNC] Starting email sync...", flush=True)

        # Check if Gmail is set up
        token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
        if not os.path.exists(token_path):
            print("[SYNC] ERROR: token.json not found — Gmail not connected", flush=True)
            raise HTTPException(
                status_code=400,
                detail="Gmail not connected. Please complete setup first."
            )
        
        print("[SYNC] token.json found, initializing Gmail client...", flush=True)
        gmail_client = GmailClient()
        ai_classifier = AIClassifier()
        
        # Fetch emails
        print(f"[SYNC] Fetching up to {max_emails} emails from Gmail...", flush=True)
        emails = gmail_client.search_job_emails(max_results=max_emails)
        print(f"[SYNC] Fetched {len(emails)} emails", flush=True)
        
        processed_count = 0
        new_applications = 0
        updated_applications = 0
        processed_threads_in_batch = set()  # Track threads processed in this batch

        def naive_utc(dt):
            """Convert any datetime to UTC-naive for SQLite storage."""
            if dt is None:
                return None
            if dt.tzinfo is not None:
                from datetime import timezone
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        for i, email in enumerate(emails, 1):
            print(f"[SYNC] [{i}/{len(emails)}] Processing: {email.get('subject', '(no subject)')[:80]}", flush=True)

            # Check if already processed
            existing_log = db.query(EmailProcessingLog).filter(
                EmailProcessingLog.gmail_message_id == email['message_id']
            ).first()
            
            if existing_log:
                print(f"[SYNC]   -> Already processed, skipping", flush=True)
                continue
            
            # Check if thread already processed in this batch
            if email['thread_id'] in processed_threads_in_batch:
                print(f"[SYNC]   -> Thread already processed in this batch, logging email only", flush=True)
                log = EmailProcessingLog(
                    gmail_message_id=email['message_id'],
                    classification='DUPLICATE_THREAD'
                )
                db.add(log)
                processed_count += 1
                continue
            
            # Classify email
            print(f"[SYNC]   -> Classifying with AI...", flush=True)
            classification = ai_classifier.classify_email(email)
            print(f"[SYNC]   -> Result: {classification['status']} ({classification['confidence']:.0%} confidence) | {classification.get('company','?')} - {classification.get('role','?')}", flush=True)
            
            # Skip if classification failed or is OTHER
            if classification['status'] == 'OTHER' and classification['confidence'] < 0.5:
                print(f"[SYNC]   -> Skipping (OTHER with low confidence)", flush=True)
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
                    'JOB_ALERT': 0,
                    'OTHER': 0
                }
                
                new_priority = status_priority.get(classification['status'], 0)
                old_priority = status_priority.get(existing_app.status, 0)
                
                if new_priority > old_priority or naive_utc(email['date']) > (existing_app.last_email_date or datetime.min):
                    existing_app.status = classification['status']
                    existing_app.confidence = classification['confidence']
                    existing_app.last_email_subject = email['subject']
                    existing_app.last_email_from = email.get('from', '')
                    existing_app.last_email_snippet = email['snippet']
                    existing_app.last_email_body = email.get('body', '')
                    existing_app.last_email_date = naive_utc(email['date'])
                    existing_app.updated_at = datetime.utcnow()
                    
                    # Append message ID
                    message_ids = json.loads(existing_app.gmail_message_ids or '[]')
                    if email['message_id'] not in message_ids:
                        message_ids.append(email['message_id'])
                        existing_app.gmail_message_ids = json.dumps(message_ids)
                    
                    updated_applications += 1
                    print(f"[SYNC]   -> Updated existing application", flush=True)
                else:
                    print(f"[SYNC]   -> Existing app has higher/equal priority, no update", flush=True)
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
                    last_email_from=email.get('from', ''),
                    last_email_snippet=email['snippet'],
                    last_email_body=email.get('body', ''),
                    last_email_date=naive_utc(email['date'])
                )
                db.add(new_app)
                new_applications += 1
                print(f"[SYNC]   -> Created new application", flush=True)
            
            # Mark thread as processed in this batch
            processed_threads_in_batch.add(email['thread_id'])
            
            # Log as processed
            log = EmailProcessingLog(
                gmail_message_id=email['message_id'],
                classification=classification['status']
            )
            db.add(log)
            processed_count += 1
        
        db.commit()

        print(f"[SYNC] Done! Processed={processed_count}, New={new_applications}, Updated={updated_applications}", flush=True)
        
        return {
            "success": True,
            "emails_fetched": len(emails),
            "emails_processed": processed_count,
            "new_applications": new_applications,
            "updated_applications": updated_applications
        }
        
    except Exception as e:
        print(f"[SYNC] ERROR: {e}", flush=True)
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
                "last_email_from": app.last_email_from,
                "last_email_snippet": app.last_email_snippet,
                "last_email_body": app.last_email_body,
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
    for status in ['APPLIED', 'INTERVIEW', 'REJECTION', 'OFFER', 'GHOSTED', 'JOB_ALERT', 'OTHER']:
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


# Reset all data (clear DB for re-sync)
@app.post("/api/reset-data")
async def reset_data(db: Session = Depends(get_db)):
    """Delete all job applications and email processing logs so emails can be re-synced."""
    deleted_apps = db.query(JobApplication).delete()
    deleted_logs = db.query(EmailProcessingLog).delete()
    db.commit()
    print(f"[RESET] Cleared {deleted_apps} applications and {deleted_logs} email logs", flush=True)
    return {"success": True, "deleted_applications": deleted_apps, "deleted_logs": deleted_logs}


# Logout — delete token.json so onboarding triggers again
@app.post("/api/logout")
async def logout():
    """Remove Gmail token so onboarding runs again on next visit."""
    token_path = os.path.join(os.path.dirname(__file__), '..', '..', 'token.json')
    if os.path.exists(token_path):
        os.remove(token_path)
        print("[LOGOUT] token.json removed", flush=True)
    return {"success": True}
@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'index.html')
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Job Application Tracker API - Frontend not found"}


# Serve onboarding page
@app.get("/onboarding")
async def serve_onboarding():
    """Serve the onboarding HTML."""
    onboarding_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'onboarding.html')
    if os.path.exists(onboarding_path):
        return FileResponse(onboarding_path)
    return {"message": "Onboarding page not found"}


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
