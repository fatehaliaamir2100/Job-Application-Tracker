"""AI-powered email classification using Ollama."""
import json
import re
from typing import Dict, Optional
import ollama
from .config import settings


class AIClassifier:
    """Classifier for job application emails using local Ollama models."""
    
    def __init__(self):
        self.model = settings.ollama_model
        self.client = ollama.Client(host=settings.ollama_base_url)
    
    def classify_email(self, email_data: Dict) -> Dict:
        """
        Classify a job-related email.
        
        Args:
            email_data: Dictionary with 'subject', 'snippet', 'body', 'from'
            
        Returns:
            Dictionary with classification results:
            {
                'status': str,  # APPLIED, INTERVIEW, REJECTION, OFFER, GHOSTED, OTHER
                'company': str,
                'role': str,
                'confidence': float
            }
        """
        # Prepare email context
        subject = email_data.get('subject', '')
        snippet = email_data.get('snippet', '')
        body = email_data.get('body', '')[:2000]  # Limit body length
        from_email = email_data.get('from', '')
        
        # Try keyword-based classification first (faster + more reliable)
        quick_classification = self._quick_classify(subject, snippet, body)
        if quick_classification:
            return quick_classification
        
        # Fall back to AI classification
        return self._ai_classify(subject, snippet, body, from_email)
    
    def _quick_classify(self, subject: str, snippet: str, body: str) -> Optional[Dict]:
        """Fast keyword-based classification for obvious cases."""
        text = (subject + ' ' + snippet + ' ' + body).lower()
        
        # Rejection keywords
        rejection_keywords = [
            'regret to inform', 'not moving forward', 'not selected',
            'other candidates', 'better fit', 'not advance',
            'unfortunately', 'pursue other candidates', 'will not be moving'
        ]
        
        # Interview keywords
        interview_keywords = [
            'interview', 'schedule a call', 'next steps',
            'would like to speak', 'phone screen', 'meet with',
            'video call', 'zoom meeting', 'teams meeting'
        ]
        
        # Offer keywords
        offer_keywords = [
            'offer', 'congratulations', 'pleased to offer',
            'joining our team', 'start date', 'compensation package'
        ]
        
        # Application confirmation keywords
        applied_keywords = [
            'thank you for applying', 'received your application',
            'application received', 'application for the position'
        ]
        
        # Check for rejection
        for keyword in rejection_keywords:
            if keyword in text:
                return {
                    'status': 'REJECTION',
                    'company': self._extract_company(text),
                    'role': self._extract_role(subject),
                    'confidence': 0.9
                }
        
        # Check for offer
        for keyword in offer_keywords:
            if keyword in text:
                return {
                    'status': 'OFFER',
                    'company': self._extract_company(text),
                    'role': self._extract_role(subject),
                    'confidence': 0.95
                }
        
        # Check for interview
        for keyword in interview_keywords:
            if keyword in text:
                return {
                    'status': 'INTERVIEW',
                    'company': self._extract_company(text),
                    'role': self._extract_role(subject),
                    'confidence': 0.85
                }
        
        # Check for application confirmation
        for keyword in applied_keywords:
            if keyword in text:
                return {
                    'status': 'APPLIED',
                    'company': self._extract_company(text),
                    'role': self._extract_role(subject),
                    'confidence': 0.8
                }
        
        return None
    
    def _ai_classify(self, subject: str, snippet: str, body: str, from_email: str) -> Dict:
        """Use Ollama AI to classify email."""
        prompt = f"""You are an expert at analyzing job application emails. Classify this email into one of these categories:
- APPLIED: Confirmation that application was received
- INTERVIEW: Invitation for interview, phone screen, or next steps
- REJECTION: Application was rejected or not moving forward
- OFFER: Job offer extended
- OTHER: General job-related email that doesn't fit above

Also extract:
- Company name
- Job role/position

Email Details:
From: {from_email}
Subject: {subject}
Content: {snippet}

{body[:1000]}

Return ONLY valid JSON in this exact format:
{{
  "status": "APPLIED|INTERVIEW|REJECTION|OFFER|OTHER",
  "company": "Company Name",
  "role": "Job Title",
  "confidence": 0.0-1.0
}}"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.1,  # Low temperature for consistent output
                }
            )
            
            # Extract JSON from response
            content = response['message']['content']
            
            # Try to parse JSON
            # Look for JSON block in markdown code fence
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                json_str = json_match.group(0) if json_match else content
            
            result = json.loads(json_str)
            
            # Validate and set defaults
            return {
                'status': result.get('status', 'OTHER'),
                'company': result.get('company', 'Unknown'),
                'role': result.get('role', 'Unknown Position'),
                'confidence': float(result.get('confidence', 0.5))
            }
            
        except Exception as e:
            print(f"AI classification error: {e}")
            # Fallback to basic extraction
            return {
                'status': 'OTHER',
                'company': self._extract_company(subject + ' ' + snippet),
                'role': self._extract_role(subject),
                'confidence': 0.3
            }
    
    def _extract_company(self, text: str) -> str:
        """Extract company name from text (simple heuristic)."""
        # Look for common patterns like "at Company" or "from Company"
        patterns = [
            r'at ([A-Z][A-Za-z0-9\s&]+?)(?:\s+for|\s+regarding|\.|,)',
            r'from ([A-Z][A-Za-z0-9\s&]+?)(?:\s+for|\s+regarding|\.|,)',
            r'join ([A-Z][A-Za-z0-9\s&]+?)(?:\s+as|\s+for|\.|,)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return "Unknown Company"
    
    def _extract_role(self, subject: str) -> str:
        """Extract role from subject line."""
        # Look for patterns like "Position:" or "for Position"
        patterns = [
            r'(?:for|as) ([A-Z][A-Za-z\s]+?)(?:\s+at|\s+-|\||$)',
            r'([A-Z][A-Za-z\s]+?) (?:Position|Role|Opportunity)',
            r'Application.*?([A-Z][A-Za-z\s]+?)(?:\s+at|\s+-|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, subject)
            if match:
                return match.group(1).strip()
        
        return "Unknown Position"
