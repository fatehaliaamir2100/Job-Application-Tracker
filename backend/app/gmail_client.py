"""Gmail API client for fetching and processing emails."""
import os
import re
import html
import base64
from html.parser import HTMLParser
from typing import List, Dict, Optional
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .config import settings

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailClient:
    """Client for interacting with Gmail API."""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth 2.0."""
        creds = None
        
        # Load existing token
        if os.path.exists(settings.gmail_token_file):
            creds = Credentials.from_authorized_user_file(
                settings.gmail_token_file, SCOPES
            )
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(settings.gmail_credentials_file):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {settings.gmail_credentials_file}\n"
                        "Please download from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(settings.gmail_token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
    
    def search_job_emails(self, max_results: int = 50) -> List[Dict]:
        """
        Search for job-related emails.
        
        Args:
            max_results: Maximum number of emails to return
            
        Returns:
            List of email dictionaries with content
        """
        try:
            # Job-related search query
            query = (
                '(subject:(application OR interview OR position OR role OR '
                'opportunity OR recruiter OR hiring OR "thank you for applying" OR '
                '"we regret" OR "moving forward" OR "next steps")) OR '
                'from:(linkedin.com OR greenhouse.io OR lever.co OR workday.com OR '
                'indeed.com OR jobs@* OR recruiting@* OR talent@* OR hr@*)'
            )
            
            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            # Fetch full message details
            emails = []
            for msg in messages:
                email_data = self._get_message_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information about a specific message."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract key headers
            subject = self._get_header(headers, 'Subject')
            from_email = self._get_header(headers, 'From')
            date_str = self._get_header(headers, 'Date')
            
            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.utcnow()
            
            # Get email body
            body = self._get_message_body(message['payload'])
            
            # Get snippet (preview)
            snippet = message.get('snippet', '')
            
            # Thread ID for grouping
            thread_id = message.get('threadId', '')
            
            return {
                'message_id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'from': from_email,
                'date': date,
                'snippet': snippet,
                'body': body
            }
            
        except HttpError as error:
            print(f'Error fetching message {message_id}: {error}')
            return None
    
    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract a specific header value."""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ''
    
    def _get_message_body(self, payload: Dict) -> str:
        """Extract message body from payload, preferring HTML for richer content."""
        html_body = ''
        plain_body = ''

        def extract_parts(p):
            nonlocal html_body, plain_body
            mime = p.get('mimeType', '')
            if mime == 'text/plain' and not plain_body:
                data = p.get('body', {}).get('data', '')
                if data:
                    plain_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            elif mime == 'text/html' and not html_body:
                data = p.get('body', {}).get('data', '')
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            for sub in p.get('parts', []):
                extract_parts(sub)

        extract_parts(payload)

        if html_body:
            return self._html_to_clean_text(html_body)
        return self._clean_plain_text(plain_body)

    def _html_to_clean_text(self, raw_html: str) -> str:
        """Convert HTML email to clean readable text."""
        # Drop <style>, <script>, <head> blocks entirely
        raw_html = re.sub(r'<(style|script|head)[^>]*>.*?</\1>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
        # Block-level tags → newline
        raw_html = re.sub(r'<(br|tr|li|p|div|h[1-6]|blockquote|hr)\b[^>]*/?>', '\n', raw_html, flags=re.IGNORECASE)
        raw_html = re.sub(r'</(p|div|h[1-6]|blockquote|ul|ol|table)>', '\n', raw_html, flags=re.IGNORECASE)
        # Strip remaining tags
        raw_html = re.sub(r'<[^>]+>', '', raw_html)
        # Unescape HTML entities
        text = html.unescape(raw_html)
        return self._clean_plain_text(text)

    def _clean_plain_text(self, text: str) -> str:
        """Remove tracking links, footers, boilerplate, and junk from plain text."""
        # Strip invisible Unicode spacer characters used as email spacers
        # (U+034F ͏, soft hyphen, zero-width spaces, BOM, etc.)
        text = re.sub(r'[\u034f\u00ad\u200b\u200c\u200d\u2060\ufeff]+', '', text)

        lines = text.splitlines()
        cleaned = []
        skip_rest = False

        for line in lines:
            stripped = line.strip()

            # Once we hit LinkedIn/Glassdoor boilerplate section headers, skip everything after
            if re.search(
                r'^(Top jobs (looking for|for) your|Search for more related jobs'
                r'|Get the new LinkedIn|Also available on mobile'
                r'|You are receiving)',
                stripped, re.IGNORECASE
            ):
                skip_rest = True

            if skip_rest:
                continue

            # Skip lines that are only invisible/whitespace characters
            visible = re.sub(r'[\u034f\u00ad\u200b\u200c\u200d\u2060\ufeff\s]', '', stripped)
            if stripped and not visible:
                continue

            # Skip bare URLs (tracking/unsubscribe links)
            if re.match(r'^https?://\S+$', stripped):
                continue

            # Skip "See more/all jobs" boilerplate
            if re.match(r'^See (more|all) jobs', stripped, re.IGNORECASE):
                continue

            # Skip common footer patterns
            if re.search(
                r'unsubscribe|opt.?out|privacy.?policy|terms.of.service'
                r'|you.?re receiving|learn why we included|intended for'
                r'|linkedin corporation|© \d{4}|all rights reserved'
                r'|do not reply|noreply|no-reply',
                stripped, re.IGNORECASE
            ):
                continue

            cleaned.append(line)

        # Collapse 3+ consecutive blank lines to 2
        result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
        return result.strip()
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread."""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                msg_data = self._get_message_details(msg['id'])
                if msg_data:
                    messages.append(msg_data)
            
            return messages
            
        except HttpError as error:
            print(f'Error fetching thread {thread_id}: {error}')
            return []
