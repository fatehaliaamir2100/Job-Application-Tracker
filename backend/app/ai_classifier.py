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

        # Job alert detection — check subject first (very reliable pattern)
        job_alert_patterns = [
            r'\bjobs similar to\b',
            r'\bnew jobs similar to\b',
            r'\bjob alert\b',
            r'\bjobs for you\b',
            r'\bnew jobs matching\b',
            r'\bjobs you might like\b',
            r'\brecommended jobs\b',
            r'\d+ new jobs',
            r'\bjobs based on your\b',
            r'\bviewed jobs\b',
        ]
        for pattern in job_alert_patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                role, company = self._extract_from_subject(subject)
                return {
                    'status': 'JOB_ALERT',
                    'company': company or 'Job Alert',
                    'role': role or 'Multiple Positions',
                    'confidence': 0.95
                }

        # Extract role and company from subject (most reliable source)
        role, company = self._extract_from_subject(subject)

        # If subject didn't give us role/company, try extracting from body
        if not role or not company:
            b_role, b_company = self._extract_from_body(body)
            role = role or b_role
            company = company or b_company

        # Rejection keywords
        rejection_keywords = [
            'regret to inform', 'not moving forward', 'not selected',
            'other candidates', 'better fit', 'not advance',
            'unfortunately', 'pursue other candidates', 'will not be moving',
            'decided not to', 'not proceed', 'not been selected',
            'did not select', 'unable to move',
            'will not be proceeding', 'not be proceeding', 'not proceeding',
            'we regret', 'no longer considering', 'position has been filled',
            'not shortlisted', 'unsuccessful', 'not successful',
        ]
        for keyword in rejection_keywords:
            if keyword in text:
                return {
                    'status': 'REJECTION',
                    'company': company or self._extract_company(text),
                    'role': role or self._extract_role(subject),
                    'confidence': 0.9
                }

        # Offer keywords
        offer_keywords = [
            'pleased to offer', 'joining our team', 'start date',
            'compensation package', 'we would like to offer', 'formal offer',
        ]
        for keyword in offer_keywords:
            if keyword in text:
                return {
                    'status': 'OFFER',
                    'company': company or self._extract_company(text),
                    'role': role or self._extract_role(subject),
                    'confidence': 0.95
                }

        # Interview keywords
        interview_keywords = [
            'interview', 'schedule a call', 'next steps',
            'would like to speak', 'phone screen', 'meet with',
            'video call', 'zoom meeting', 'teams meeting', 'google meet',
            'availability', 'calendar invite', 'book a time',
        ]
        for keyword in interview_keywords:
            if keyword in text:
                return {
                    'status': 'INTERVIEW',
                    'company': company or self._extract_company(text),
                    'role': role or self._extract_role(subject),
                    'confidence': 0.85
                }

        # Application confirmation keywords
        applied_keywords = [
            'thank you for applying', 'received your application',
            'application received', 'application for the position',
            'we have received your', 'successfully submitted',
        ]
        for keyword in applied_keywords:
            if keyword in text:
                return {
                    'status': 'APPLIED',
                    'company': company or self._extract_company(text),
                    'role': role or self._extract_role(subject),
                    'confidence': 0.8
                }

        # If subject gave us role+company and body mentions "applied on", classify as APPLIED
        if role and company and re.search(r'applied on', text, re.IGNORECASE):
            return {
                'status': 'APPLIED',
                'company': company,
                'role': role,
                'confidence': 0.75
            }

        return None
    
    def _ai_classify(self, subject: str, snippet: str, body: str, from_email: str) -> Dict:
        """Use Ollama AI to classify email."""
        prompt = f"""You are an expert job application email classifier. Analyze this email carefully.

SUBJECT: {subject}
FROM: {from_email}
BODY:
{body[:2000]}

CLASSIFICATION RULES — pick exactly one status:
- APPLIED: Application confirmation (e.g. "thank you for applying", "application received", "applied on [date]")
- INTERVIEW: Interview invitation or scheduling (e.g. "schedule a call", "phone screen", "next steps", "meet with")
- REJECTION: Application declined (e.g. "not moving forward", "will not be proceeding", "regret to inform", "unfortunately", "other candidates", "not selected")
- OFFER: Job offer extended (e.g. "pleased to offer", "start date", "compensation package")
- JOB_ALERT: Email only contains job listings/recommendations, NOT a specific application update (e.g. "jobs similar to", "jobs for you", "recommended jobs")
- OTHER: General recruiter outreach or cannot be classified

EXTRACTION RULES — extract company and role from the email:
1. Check SUBJECT first for patterns like "application to [ROLE] at [COMPANY]".
   Example: "Your application to AI Engineer at Motorola Solutions" → role="AI Engineer", company="Motorola Solutions"
2. If not found in subject, scan the BODY for phrases like:
   - "apply for the [ROLE] position at [COMPANY]"
   - "applied for [ROLE] at [COMPANY]"
   - "your interest in the [ROLE] position at [COMPANY]"
   - "[ROLE] role at [COMPANY]"
   Example body: "Thank you for applying for the Software Engineer position at Virtuagym" → role="Software Engineer", company="Virtuagym"
3. CONFIDENCE: Float 0.0–1.0 reflecting your certainty.

Return ONLY valid JSON, no explanation, no markdown:
{{
  "status": "APPLIED|INTERVIEW|REJECTION|OFFER|JOB_ALERT|OTHER",
  "company": "Company Name",
  "role": "Job Title",
  "confidence": 0.0
}}"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.1,
                }
            )

            content = response['message']['content']

            # Try to parse JSON from markdown code fence first
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                json_str = json_match.group(0) if json_match else content

            result = json.loads(json_str)

            return {
                'status': result.get('status', 'OTHER'),
                'company': result.get('company', 'Unknown'),
                'role': result.get('role', 'Unknown Position'),
                'confidence': float(result.get('confidence', 0.5))
            }

        except Exception as e:
            print(f"AI classification error: {e}")
            role, company = self._extract_from_subject(subject)
            return {
                'status': 'OTHER',
                'company': company or self._extract_company(subject + ' ' + snippet),
                'role': role or self._extract_role(subject),
                'confidence': 0.3
            }
    
    def _extract_from_body(self, body: str) -> tuple:
        """Extract (role, company) from email body text as a fallback."""
        patterns = [
            # "apply/applied for the ROLE position at COMPANY"
            r'appl(?:y|ied|ying) for (?:the )?(.+?) (?:position|role|opportunity) at ([A-Z][A-Za-z0-9\s&.,]+?)(?:\.|,|\n|$)',
            # "your interest in the ROLE position at COMPANY"
            r'interest in (?:the )?(.+?) (?:position|role) at ([A-Z][A-Za-z0-9\s&.,]+?)(?:\.|,|\n|$)',
            # "ROLE position at COMPANY"
            r'([A-Z][A-Za-z0-9\s()/-]+?) (?:position|role) at ([A-Z][A-Za-z0-9\s&.,]+?)(?:\.|,|\n|$)',
            # "ROLE at COMPANY" as a standalone phrase
            r'(?:the )?([A-Z][A-Za-z0-9\s()/-]{3,40}?) at ([A-Z][A-Za-z][A-Za-z0-9\s&.,]{2,40}?)(?:\s+in\s|\.|,|\n|$)',
        ]
        for pattern in patterns:
            m = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
            if m:
                role = m.group(1).strip().rstrip('.')
                company = m.group(2).strip().rstrip('.')
                # Sanity check: skip overly generic matches
                skip_roles = {'your', 'this', 'our', 'the', 'a', 'an', 'thank you'}
                if role.lower() not in skip_roles and 2 < len(role) < 80 and 2 < len(company) < 80:
                    return role, company
        return '', ''

    def _extract_from_subject(self, subject: str) -> tuple:
        """Extract (role, company) from subject line using common email patterns."""
        # "Your application to ROLE at COMPANY" — LinkedIn standard
        m = re.search(r'application (?:to|for)\s+(.+?)\s+at\s+(.+?)(?:\s+in\s|\s*$)', subject, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # "(New) jobs similar to ROLE at COMPANY" — LinkedIn job alerts
        m = re.search(r'(?:new\s+)?jobs similar to\s+(.+?)\s+at\s+(.+?)(?:\s+in\s|\s*$)', subject, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # "job alert: ROLE at COMPANY" style
        m = re.search(r'job alert[:\s]+\s*(.+?)\s+at\s+(.+?)(?:\s+in\s|\s*$)', subject, re.IGNORECASE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        # "ROLE at COMPANY - ..." or "ROLE at COMPANY | ..."
        m = re.search(r'^(.+?)\s+at\s+([^-|,\n]+?)(?:\s*[-|,]|\s*$)', subject, re.IGNORECASE)
        if m:
            role, company = m.group(1).strip(), m.group(2).strip()
            skip = {'thank you', 'congratulations', 'update', 'your', 'an update'}
            if role.lower() not in skip and len(role) > 3 and len(company) > 2:
                return role, company

        return '', ''

    def _extract_company(self, text: str) -> str:
        """Extract company name from text (fallback heuristic)."""
        patterns = [
            r'(?:from|at|by|with)\s+([A-Z][A-Za-z0-9\s&.,]+?)(?:\s+(?:for|regarding|in|is|has|would|will)|\.|,|$)',
            r'([A-Z][A-Za-z0-9\s&]+?)\s+(?:team|recruiting|talent|hr)\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(1).strip()
                if 2 < len(candidate) < 50:
                    return candidate
        return 'Unknown Company'

    def _extract_role(self, subject: str) -> str:
        """Extract job role from subject line (fallback heuristic)."""
        patterns = [
            r'application (?:to|for)\s+(.+?)\s+at\s',
            r'(?:for|as)\s+([A-Z][A-Za-z\s()]+?)(?:\s+at|\s+-|\||$)',
            r'([A-Z][A-Za-z\s]+?)\s+(?:Position|Role|Opportunity)\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, subject, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return 'Unknown Position'
