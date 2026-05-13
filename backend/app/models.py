"""Database models for job applications."""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from datetime import datetime
from .database import Base


class JobApplication(Base):
    """Job application tracking model."""
    
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job details
    company = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    
    # Status tracking
    status = Column(String, nullable=False, index=True)  # APPLIED, INTERVIEW, REJECTION, OFFER, GHOSTED, JOB_ALERT, OTHER
    confidence = Column(Float, default=1.0)
    
    # Email tracking
    gmail_thread_id = Column(String, unique=True, index=True)
    gmail_message_ids = Column(Text)  # JSON array of message IDs
    last_email_subject = Column(String)
    last_email_from = Column(String)
    last_email_snippet = Column(Text)
    last_email_body = Column(Text)
    last_email_date = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    notes = Column(Text)
    
    def __repr__(self):
        return f"<JobApplication(company='{self.company}', role='{self.role}', status='{self.status}')>"


class EmailProcessingLog(Base):
    """Log of processed emails to avoid reprocessing."""
    
    __tablename__ = "email_processing_log"
    
    id = Column(Integer, primary_key=True, index=True)
    gmail_message_id = Column(String, unique=True, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    classification = Column(String)
    
    def __repr__(self):
        return f"<EmailProcessingLog(message_id='{self.gmail_message_id}')>"
